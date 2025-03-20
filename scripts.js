document.addEventListener("DOMContentLoaded", function () {
    const loginForm = document.querySelector("form");

    loginForm.addEventListener("submit", async function (event) {
        event.preventDefault(); // Impede o envio padrão do formulário

        const username = document.querySelector("input[name='username']").value;
        const password = document.querySelector("input[name='password']").value;
        
        try {
            const response = await fetch("/api/login", { // Agora chama a API localmente
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ username, password })
            });
        
            const data = await response.json();
        
            if (data.success) {
                let userId = data.user_id; // Armazena o ID do usuário na variável
                console.log("User ID:", userId); // Escreve o ID no console
                sessionStorage.setItem("user_id", userId);
                window.location.href = "/posLogin/inicio.html";
            }
            else {
                alert("Usuário ou senha incorretos");
            }
        } catch (error) {
            console.error("Erro ao conectar com o servidor", error);
            alert("Erro ao tentar fazer login. Tente novamente.");
        }
            
    });
});

