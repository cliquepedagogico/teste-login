document.addEventListener("DOMContentLoaded", function () {
    let userId = sessionStorage.getItem("user_id");
    if (userId) {
        
        console.log("Usuário logado com ID:", userId);
    } else {
        alert("Nenhum usuário logado. Redirecionando para login...");
        window.location.href = "index.hmtl"; // Ajuste para a página de login correta
    }
});
