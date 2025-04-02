//animação de texto
const texto1 = document.getElementById('texto1');
    const texto2 = document.getElementById('texto2');
    let mostrando1 = true;

    setInterval(() => {
      if (mostrando1) {
        texto1.classList.remove('ativo');
        texto1.classList.add('inativo');

        texto2.classList.remove('inativo');
        texto2.classList.add('ativo');
      } else {
        texto2.classList.remove('ativo');
        texto2.classList.add('inativo');

        texto1.classList.remove('inativo');
        texto1.classList.add('ativo');
      }

      mostrando1 = !mostrando1;
    }, 3000);
//animação de texto

//Deixa a barra de paginas fixa
const navbar = document.getElementById("navbarMenu");
const social = document.getElementById("socialBar");
const triggerAltura = social.offsetHeight;

window.addEventListener("scroll", () => {
  if (window.scrollY >= triggerAltura) {
    navbar.classList.add("fixa");
    social.classList.add("oculta");
  } else {
    navbar.classList.remove("fixa");
    social.classList.remove("oculta");
  }
});
//Deixa a barra de paginas fixa

//conteiner animado
const questions = document.querySelectorAll(".faq-question");

questions.forEach((question) => {
  question.addEventListener("click", () => {
    // Fecha todos os outros
    questions.forEach((q) => {
      if (q !== question) {
        q.classList.remove("active");
        q.nextElementSibling.style.maxHeight = null;
      }
    });

    // Alterna o atual
    question.classList.toggle("active");
    const answer = question.nextElementSibling;

    if (question.classList.contains("active")) {
      answer.style.maxHeight = answer.scrollHeight + "px";
    } else {
      answer.style.maxHeight = null;
    }
  });
});
//conteiner animado