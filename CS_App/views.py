from django.shortcuts import render 
from django.http import JsonResponse,HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt 
import json
from .models import Message  # 確保只 import 一次
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

# LangChain 相關
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings 
from langchain.schema import Document 
from langchain_text_splitters import CharacterTextSplitter 
from langchain_community.vectorstores import FAISS 
from langchain.chains import ConversationalRetrievalChain 
from langchain.memory import ConversationSummaryBufferMemory 

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import fitz  # PyMuPDF 
import os
import markdown2
from django.utils.safestring import mark_safe

from django.contrib.auth.forms import UserCreationForm



#LINE BOT API
line_bot_api = LineBotApi(settings.LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(settings.LINE_CHANNEL_SECRET)

# 設置 Google API 金鑰
os.environ["GOOGLE_API_KEY"] = "AIzaSyAIpYdu1yFJvm-a6SRx7MeBP86HIaRG2xc"

# 📌 **聊天頁面 (chat_view)**
def chat_view(request):
    messages = Message.objects.all().order_by('timestamp')
    for msg in messages:
        msg.rendered_content = mark_safe(
            markdown2.markdown(
                msg.content,
                extras=["fenced-code-blocks", "strike", "tables"]
            )
        )
    return render(request, 'chat.html', {'content': messages})

# 📌 **處理用戶發送的訊息**
@csrf_exempt
def send_message(request):
    if request.method == "POST":
        data = json.loads(request.body)
        new_msg = Message(username=data['username'], content=data['content'])
        new_msg.save()
        return JsonResponse({'status': 'success'})

# 📌 **載入 PDF 檔案並轉換為文本**
def load_pdf(file_path):
    pdf_document = fitz.open(file_path)
    pdf_text = ""
    for page_num in range(pdf_document.page_count):
        page = pdf_document.load_page(page_num)
        pdf_text += page.get_text("text")  # type: ignore
    return pdf_text

# **處理 PDF 轉向量**
pdf_text = load_pdf("D:/VS/DJN3/djn3/CS_Project/CS_App/TEST/Resume.pdf")
document = Document(page_content=pdf_text, metadata={})
text_splitter = CharacterTextSplitter(chunk_size=100, chunk_overlap=10)
texts = text_splitter.split_documents([document])
embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
db = FAISS.from_documents(texts, embeddings)

retriever = db.as_retriever()
llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro")
memory = ConversationSummaryBufferMemory(llm=llm, memory_key="chat_history", return_messages=True)

# 建立 LangChain 對話鏈
chain = ConversationalRetrievalChain.from_llm(
    llm=llm,
    retriever=retriever,
    memory=memory
)

# 📌 **AI 聊天 API**
@csrf_exempt
def chat_api(request):
    if request.method == "POST":
        data = json.loads(request.body)
        user_message = data.get("message", "")

        if not user_message:
            return JsonResponse({"error": "No message provided"}, status=400)

        result = chain.invoke({"question": user_message})
        bot_response = result["answer"]

        return JsonResponse({"response": bot_response})
    
@csrf_exempt
def line_webhook(request):
    if request.method == "POST":
        signature = request.headers.get("X-Line-Signature")
        body = request.body.decode("utf-8")

        try:
            handler.handle(body, signature)
        except InvalidSignatureError:
            return HttpResponse(status=400)

        return HttpResponse("OK")

    return HttpResponse("This endpoint is for LINE Webhook only.")

@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    user_message = event.message.text
    result = chain.invoke({"question": user_message})
    bot_response = result["answer"]
    reply_message = f"{bot_response}"
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_message))

from django.contrib.auth.models import User

# 登入畫面
def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('/chat/')  # 登入成功後導向聊天頁面
        else:
            return render(request, 'login.html', {'error': '登入失敗，請檢查帳號或密碼'})

    return render(request, 'login.html')

# 登出功能
###def logout_view(request):
    logout(request)
    return redirect(' ')
###
def register_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password1 = request.POST['password1']
        password2 = request.POST['password2']

        if password1 != password2:
            return render(request, 'register.html', {'error_message': '密碼不一致'})

        # 建立使用者帳號
        user = User.objects.create_user(username=username, email=email, password=password1)
        user.save()

        return redirect('login')  # 或跳轉到首頁等等

    return render(request, 'register.html')
