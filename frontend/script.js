const inputbar = document.getElementById("user-input");
const but = document.getElementById("send-button");
const output = document.getElementById("chat-window");

but.addEventListener("click", async function () {
  const prompt = inputbar.value.trim();

  if (!prompt) return;

  const userBubble = document.createElement("div");
  userBubble.classList.add("message", "user");
  userBubble.textContent = prompt;
  output.appendChild(userBubble);

  inputbar.value = "";

  const bubble = document.createElement("div");
  bubble.classList.add("message", "loading");
  bubble.textContent = "Thinking ...";
  output.appendChild(bubble);

  output.scrollTop = output.scrollHeight;

  try {
    const response = await fetch("http://127.0.0.1:5000/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: prompt })
    });

    const data = await response.json();

    const reply = document.createElement("div");
    reply.classList.add("message", "bot");
    reply.textContent = data.reply || data.error;

    bubble.remove();
    output.appendChild(reply);

  } catch (error) {
    bubble.remove();
    console.log("Error:", error);
  }

  output.scrollTop = output.scrollHeight;
});
