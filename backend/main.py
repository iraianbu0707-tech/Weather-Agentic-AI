import os
from google import genai
from google.genai import types
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

load_dotenv()


# ---------- Real tool function ----------

def get_weather(city):
    city_name = city.lower()
    url_cords = f"https://geocoding-api.open-meteo.com/v1/search?name={city_name}&count=1"
    response1 = requests.get(url_cords)
    data1 = response1.json()
    results = data1.get("results")
    if not results:
        return f"no city named {city}"
    lat = results[0]["latitude"]
    lon = results[0]["longitude"]
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
    response2 = requests.get(url)
    data2 = response2.json()
    temperature = data2["current_weather"]["temperature"]
    windspeed = data2["current_weather"]["windspeed"]
    return f"The current temperature in {city} is {temperature}°C with wind speed {windspeed} km/h."


# A lookup so we can call the right real function by name, once Gemini tells us which one it wants
AVAILABLE_FUNCTIONS = {
    "get_weather": get_weather
}


# ---------- Tool description for Gemini ----------

get_weather_declaration = types.FunctionDeclaration(
    name="get_weather",
    description="Get the current weather (temperature and windspeed) for a given city",
    parameters={
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": "The name of a city, e.g. Chennai"
            }
        },
        "required": ["city"]
    }
)

weather_tool = types.Tool(function_declarations=[get_weather_declaration])

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

app = Flask(__name__)
CORS(app)


@app.route("/ask", methods=["POST"])
def ask_agent():
    data = request.get_json()
    prompt = data.get("prompt")

    if not prompt:
        return jsonify({"error": "No prompt provided"}), 400

    contents = [
        types.Content(role="user", parts=[types.Part(text=prompt)])
    ]

    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=contents,
            config=types.GenerateContentConfig(tools=[weather_tool])
        )

        part = response.candidates[0].content.parts[0]

        # If Gemini didn't ask for a tool, just return its direct answer
        if not part.function_call:
            return jsonify({"reply": part.text})

        function_name = part.function_call.name
        function_args = part.function_call.args

        # Look up and run the real function matching what Gemini asked for
        real_function = AVAILABLE_FUNCTIONS.get(function_name)

        if not real_function:
            return jsonify({"error": f"Unknown tool requested: {function_name}"}), 500

        real_result = real_function(**function_args)

        # Add Gemini's tool-call turn, then our function's result, back into the conversation
        contents.append(response.candidates[0].content)
        contents.append(
            types.Content(
                role="user",
                parts=[types.Part.from_function_response(
                    name=function_name,
                    response={"result": real_result}
                )]
            )
        )

        final_response = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=contents,
            config=types.GenerateContentConfig(tools=[weather_tool])
        )

        return jsonify({"reply": final_response.text})

    except Exception as e:
        return jsonify({"error": "Something went wrong. Please try again."}), 500


if __name__ == "__main__":
    app.run(debug=True)