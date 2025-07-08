from django.shortcuts import render
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
import threading
import os
import subprocess
import ollama
import textwrap


# Initialize Ollama server
def _ollama():
    os.environ['OLLAMA_HOST'] = '127.0.0.1:11434'  
    os.environ['OLLAMA_ORIGINS'] = '*'
    subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def start_ollama():
    thread = threading.Thread(target=_ollama, daemon=True)
    thread.start()
    print("Starting Ollama server...")

start_ollama()


class Chat:
    def __init__(self):
        self.model = "llama3.2"
        self.history = []
        self.model_name = "veiassist_agent3"
        self.modelfile_path = "Modelfile_veriassist3"
        self.create_model()

    def create_model(self):


        modelfile_content = textwrap.dedent(f"""
FROM {self.model}
SYSTEM "You are VeriAssist — a smart, friendly AI assistant with deep expertise in **Verification Engineering**, and capable across all domains.

🧠 You can help with:
- Verification (SystemVerilog, UVM, assertions)
- Formal methods, testbenches, coverage
- Debugging protocols (AXI, PCIe), waveforms
- General tasks: explaining concepts, math, code, writing, and more.

---

🎯 **RESPONSE STYLE (STRICTLY FOLLOW):**

1. ✨ **Structure & Formatting**
   - Use headings, spacing, lists, tables, etc.
   - Start every **section heading** with a relevant emoji.
   - Also use emojis in-line where helpful (e.g., “That’s a great tip! 💡”).
   - ❌ Do NOT insert labels like `💡 Tip` or `📊 Data` as literal headings. Use **the emoji**, but **write your own text** based on the response context.

   ✅ Example:
   - GOOD:  
     **📘 What is a Stock?**  
     Stocks represent ownership in a company...

   - BAD:  
     **📘 Definition / Overview** ← (❌ Don't do this!)

2. 🧠 **Emoji Use Guidance**  
   Use emojis **naturally and meaningfully**. Pick from this set based on the meaning of the text:

   | Emoji | Use for |
   |-------|---------|
   | 👋     | Greetings / Farewells |
   | 📘     | Definitions / Intros |
   | 💡     | Tips / Ideas |
   | ✅     | Steps / Answers / Checks |
   | 📊     | Data / Finance / Analysis |
   | 🔍     | Explanations / Dives |
   | 🔧     | Tools / Setup |
   | 🧰     | UVM / Verification Components |
   | 🧪     | Tests / Experiments |
   | 🐞     | Bugs / Issues |
   | ⚠️     | Warnings / Cautions |
   | 💬     | User Questions / Quotes |
   | 💻     | Code / Terminals |
   | 🎯     | Objectives / Goals |
   | 📌     | Summaries / Key Points |
   | 🔁     | Processes / Pipelines |
   | 🤖     | Your own actions or identity |

   Feel free to mix or add others where it improves clarity or tone.

3. 🧮 **Math & LaTeX**
   - Only wrap actual math in LaTeX (`$E = mc^2$`)
   - Never use LaTeX for plain values like `$2 billion$` → write: `2 billion`

4. 🤖 **Personality**
   - Friendly, clear, and conversational
   - Greet with:  
     “Hi there! I’m VeriAssist 🤖 — your AI sidekick for Verification and more! How can I help?”
   - End chats with:  
     “Glad I could help! Feel free to reach out anytime. 👋”

5. 📌 **Memory & Follow-Ups**
   - Track and use context
   - Handle brief or casual follow-ups smoothly

---

⚠️ **Do NOT echo emoji category labels like `💡 Tip` or `📘 Definition` directly.** Choose emojis based on meaning and integrate them into your own writing.""
""")


        try:
            existing_models = ollama.list()
            model_names = [m.get('name', '') for m in existing_models.get('models', [])]
            if self.model_name in model_names:
                print("Model already exists. Skipping creation.")
                return
        except Exception as e:
            print("Could not check existing models:", e)

        # Ensure previous file is removed
        if os.path.exists(self.modelfile_path):
            os.remove(self.modelfile_path)

        # Write model file with proper encoding
        with open(self.modelfile_path, "w", encoding="utf-8") as f:
            f.write(modelfile_content.strip() + "\n")  # Ensure newline at end

        # Run Ollama command and capture errors

        try:
            result = subprocess.run(
                ["ollama", "create", self.model_name, "--file=" + self.modelfile_path],
                check=True, capture_output=True, text=True
            )
            print("Model created successfully:", result.stdout)
        except subprocess.CalledProcessError as e:
            print("Error while creating model:", e.stderr or "Unknown error.")

        finally:
            # ✅ Always delete modelfile, even if creation fails
            if os.path.exists(self.modelfile_path):
                try:
                    os.remove(self.modelfile_path)
                    print(f"Cleaned up: {self.modelfile_path}")
                except Exception as cleanup_err:
                    print("Failed to delete model file:", cleanup_err)


    def generate_response(self, question):
        question = question.lower()

        # Add user message to history
        self.history.append({'role': 'user', 'content': question})
        print(f"\nUser: {question}")  # Print user question
        
        # Create streaming response
        stream = ollama.chat(
            model=self.model_name,
            messages=self.history,
            stream=True,
            keep_alive=-1
        )
        
        # Generator function for streaming
        print("Assistant: ", end='', flush=True)  # Start assistant response print
        full_response = []
        
        for chunk in stream:
            content = chunk['message']['content']
            print(content, end='', flush=True)  # Print each chunk as it comes
            full_response.append(content)
            yield content

        # Add final response to history
        self.history.append({'role': 'assistant', 'content': ''.join(full_response)})
        print()  # New line after complete response

    def reset(self):
        self.history = []
        print("Conversation history reset.")


# chat = Chat()

# Global chat instance (set after model is ready)
chat = None

# Delayed initializer for model + warmup
def delayed_start():
    global chat
    chat = Chat()  # This creates your custom model if needed

    try:
        print("Warming up model...")
        _ = list(ollama.chat(
            model=chat.model_name,
            messages=[{"role": "user", "content": "Hi, what is verification?"}],
            stream=True
        ))
        print("------------- Model warmed up.-------------")
    except Exception as e:
        print("Warmup failed:", e)

# Start chat creation + warmup in background thread
threading.Thread(target=delayed_start, daemon=True).start()


@csrf_exempt
def chat_api(request):
    if request.method == 'POST':
        user_message = request.POST.get('message', '')
        print(f"\nReceived message: {user_message}")  # Print received message
        
        def stream_response():
            try:
                for chunk in chat.generate_response(user_message):
                    yield chunk
            except Exception as e:
                print(f"\nError during streaming: {str(e)}")
                yield f"\n[Error: {str(e)}]"
        
        return StreamingHttpResponse(stream_response(), content_type='text/plain')
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)




def index(request):
    return render(request, 'index.html')