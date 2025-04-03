let conversations = []; 
let currentConversation = [];
let conversationStarted = false;
let conversationTitle = '';
let selectedConversationId = null;
const currentDate = new Date();
const sevenDaysAgo = new Date(currentDate);

console.log("ID do usuário logado via Flask:", userId);


function scrollToBottom() {
    const chatBox = document.getElementById('chat-box');
    chatBox.scrollTop = chatBox.scrollHeight;
}

function newConversation(funcionalidade = 'tire-uma-duvida') {
    if (currentConversation.length > 0 && conversationStarted) {
        saveConversation(selectedConversationId, conversationTitle);
    }

    currentConversation = [];
    conversationTitle = '';
    conversationStarted = false;
    selectedConversationId = null;
    document.getElementById('chat-box').innerHTML = "";
    updateConversationHistory();

    if (funcionalidade === 'gerar_imagem') {
        conversationTitle = 'Nova Conversa para Imagem';
        createImage();
    }
}

function sendMessage() {
    let message = document.getElementById('user-input').value;

    

    if (message.trim() === "") {
        return;
    }

    if (conversationTitle === 'Nova Conversa para Imagem') {
        createImage();
        return;
    }

    document.getElementById('chat-box').innerHTML += `
        <div class="user-message"><p>${message}</p></div>`;
    scrollToBottom();

    let historyToSend = currentConversation.map(msg => {
        return { role: msg.role, content: msg.content };
    });

    if (!conversationStarted) {
        conversationTitle = message.substring(0, 20);
        conversationStarted = true;

        fetch('./chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, message: message, history: historyToSend })
        })
        .then(response => response.json())
        .then(data => {
            selectedConversationId = data.conversa_id;
            currentConversation.push({ "role": "user", "content": message, "type": "text" });

            if (data.response || data.image_url) {
                appendAssistantResponse(data);
            }

            saveConversation(selectedConversationId, conversationTitle);
            updateConversationHistory();
        });
    } else {
        fetch('./chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, message: message, conversa_id: selectedConversationId, history: historyToSend })
        })
        .then(response => response.json())
        .then(data => {
            currentConversation.push({ "role": "user", "content": message, "type": "text" });

            if (data.response || data.image_url) {
                appendAssistantResponse(data);
            }

            saveConversation(selectedConversationId, conversationTitle);
            updateConversationHistory();
        });
    }

    document.getElementById('user-input').value = "";
    autoResize(document.getElementById('user-input'));
}

function appendAssistantResponse(data) {
    if (data.image_url) {
        document.getElementById('chat-box').innerHTML += `
            <div class="assistant-message">
                <img src="${data.image_url}" alt="Imagem gerada" style="max-width: 60%; border-radius: 10px;">
            </div>`;
        currentConversation.push({ "role": "assistant", "content": data.image_url, "type": "image" });
    } else if (data.response) {
        document.getElementById('chat-box').innerHTML += `
            <div class="assistant-message">
                <p><strong>Vix:</strong> ${data.response}</p>
            </div>`;
        currentConversation.push({ "role": "assistant", "content": data.response, "type": "text" });
    }
    scrollToBottom();
}

function saveConversation(conversationId, title) {
    let existingConversationIndex = conversations.findIndex(conv => conv.id === conversationId);

    if (existingConversationIndex !== -1) {
        conversations[existingConversationIndex] = {
            id: conversationId,
            userId: userId,
            title: title,
            messages: currentConversation,
            lastModified: new Date()
        };
    } else {
        let newConversation = {
            id: conversationId,
            userId: userId,
            title: title,
            messages: currentConversation,
            lastModified: new Date()
        };
        conversations.push(newConversation);
    }

    updateConversationHistory();
}

function updateConversationHistory() {
    let container = document.getElementById('conversations-list');
    container.innerHTML = "";

    conversations.sort((a, b) => new Date(b.lastModified) - new Date(a.lastModified));

    conversations.forEach((conv, index) => {
        let conversationHTML = `<p><a href="#" onclick="loadConversation(${index})">${conv.title}</a></p>`;
        container.innerHTML += conversationHTML;
    });
}

function loadConversation(index) {
    let conversationId = conversations[index].id;
    selectedConversationId = conversationId;

    fetch('/carregar_mensagem', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ conversa_id: conversationId })
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById('chat-box').innerHTML = "";

        data.forEach(entry => {
            let messageClass = entry.remetente === 'user' ? 'user-message' : 'assistant-message';
            let senderName = entry.remetente === 'user' ? '' : 'Vix:';

            if (entry.mensagem.startsWith('http')) {
                document.getElementById('chat-box').innerHTML += `
                    <div class="${messageClass}">
                        <img src="${entry.mensagem}" alt="Imagem gerada" style="max-width: 60%; border-radius: 10px;">
                    </div>`;
            } else if (entry.remetente === 'vix') {
                document.getElementById('chat-box').innerHTML += `
                    <div class="${messageClass}">
                        <p><strong>${senderName}</strong> ${entry.mensagem}</p>
                    </div>`;
            } else {
                document.getElementById('chat-box').innerHTML += `
                    <div class="${messageClass}">
                        <p>${entry.mensagem}</p>
                    </div>`;
            }
        });

        currentConversation = data.map(entry => ({
            role: entry.remetente === 'user' ? 'user' : 'assistant',
            content: entry.mensagem
        }));
        conversationStarted = true;

        scrollToBottom();
    })
    .catch(error => console.error('Erro ao carregar o histórico da conversa:', error));
}

function checkEnter(event) {
    if (event.key === "Enter") {
        event.preventDefault();
        sendMessage();
    }
}

function autoResize(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = textarea.scrollHeight + 'px';
}

function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('recolhido');
    let toggleButton = document.getElementById('toggle-sidebar');
    toggleButton.textContent = document.getElementById('sidebar').classList.contains('recolhido') ? '➡' : '⬅';
}

function setUserName(userName) {
    document.getElementById('username').textContent = userName;
}

window.onload = function() {
    checkSidebarOnLoad();
};

window.onresize = function() {
    checkSidebarOnLoad();
};

function checkSidebarOnLoad() {
    const sidebar = document.getElementById('sidebar');
    const toggleButton = document.getElementById('toggle-sidebar');

    if (window.innerWidth <= 768) {
        sidebar.classList.add('recolhido');
        toggleButton.textContent = '➡';
    } else {
        sidebar.classList.remove('recolhido');
        toggleButton.textContent = '⬅';
    }
}



document.addEventListener('DOMContentLoaded', function() {
    loadConversations();

});

function mostrarImagemDaVix(imageUrl) {
    document.getElementById('chat-box').innerHTML += `
        <div class="assistant-message">
            <img src="${imageUrl}" alt="Imagem gerada" style="max-width: 60%; border-radius: 10px;">
        </div>`;
    scrollToBottom();
}

function loadConversations() {
    fetch('/carregar_conversas', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId })
    })
    .then(response => response.json())
    .then(data => {
        conversations = data.map(conv => ({
            userId: userId,
            title: conv.title,
            id: conv.id,
            messages: []
        }));

        updateConversationHistory();
    })
    .catch(error => console.error('Erro ao carregar as conversas:', error));
}

function createImage() {
    let message = document.getElementById('user-input').value;

    if (message.trim() === "") {
        return;
    }

    document.getElementById('chat-box').innerHTML += `
        <div class="user-message"><p>${message}</p></div>`;
    scrollToBottom();

    document.getElementById('chat-box').innerHTML += `
        <div class="assistant-message" id="loading-message">
            <p>Gerando imagem...</p>
        </div>`;
    scrollToBottom();

    fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            user_id: userId,
            message: message,
            funcionalidade: 'gerar_imagem'
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.image_url) {
            const loadingMessage = document.getElementById('loading-message');
            if (loadingMessage) {
                loadingMessage.remove();
            }

            document.getElementById('chat-box').innerHTML += `
                <div class="assistant-message">
                    <img src="${data.image_url}" alt="Imagem gerada" style="max-width: 60%; border-radius: 10px;">
                </div>`;
            scrollToBottom();
        }
    })
    .catch(error => console.error('Erro ao gerar a imagem:', error));

    document.getElementById('user-input').value = "";
}

function updateConversationHistory() {
    let container = document.getElementById('conversations-list');
    container.innerHTML = "";

    conversations.forEach((conv, index) => {
        container.innerHTML += `
            <div class="conversation-item">
                <span onclick="loadConversation(${index})">${conv.title}</span>
                <button class="delete-btn" onclick="confirmDelete(${conv.id})">X</button>
            </div>`;
    });
}

function confirmDelete(conversationId) {
    let confirmation = confirm("Você tem certeza que deseja excluir esta conversa?");
    if (confirmation) {
        deleteConversation(conversationId);
    }
}

function deleteConversation(conversationId) {
    fetch('/excluir_conversa', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ conversa_id: conversationId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === "Conversa excluída") {
            conversations = conversations.filter(conv => conv.id !== conversationId);
            updateConversationHistory();
        }
    })
    .catch(error => console.error('Erro ao excluir a conversa:', error));
}

console.log("final ID do usuário logado:", userId);
