function sendMessage() {
    const inputField = document.getElementById("user-input");
    const chatBox = document.getElementById("chat-box");
    const userText = inputField.value.trim();

    // 입력창이 비어있으면 무시
    if (userText === "") return;

    // 1. 사용자가 보낸 메시지를 화면에 추가
    const userMessage = document.createElement("div");
    userMessage.className = "message user";
    userMessage.innerText = "나: " + userText;
    chatBox.appendChild(userMessage);

    // 입력창 초기화
    inputField.value = "";

    // 스크롤을 맨 아래로 내리기
    chatBox.scrollTop = chatBox.scrollHeight;

    // 2. 1초 뒤에 시스템(봇)이 응답하는 상호작용 구현
    setTimeout(() => {
        const botMessage = document.createElement("div");
        botMessage.className = "message bot";
        botMessage.innerText = "상대방: '" + userText + "' 라고 말씀하셨군요!";
        chatBox.appendChild(botMessage);
        
        // 스크롤 내리기
        chatBox.scrollTop = chatBox.scrollHeight;
    }, 1000);
}
