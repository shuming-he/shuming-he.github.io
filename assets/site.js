// Shared behaviour for every page: CV link availability and back-to-top.
(function () {
  const CV_PATH = "/cv.pdf";

  function setCv(available) {
    document.querySelectorAll("[data-cv]").forEach(a => {
      const label = a.querySelector(".lbl") || a;
      if (available) {
        a.href = CV_PATH;
        a.setAttribute("download", "Shuming_He_CV.pdf");
        a.removeAttribute("aria-disabled");
        a.title = "Download CV (PDF)";
        if (a.dataset.cvLabel) label.textContent = a.dataset.cvLabel;
      } else {
        a.removeAttribute("href");
        a.setAttribute("aria-disabled", "true");
        a.title = "CV coming soon";
        if (a.dataset.cvSoon) label.textContent = a.dataset.cvSoon;
      }
    });
  }
  setCv(false);
  fetch(CV_PATH, { method: "HEAD" }).then(r => setCv(r.ok)).catch(() => setCv(false));

  document.querySelectorAll("[data-top]").forEach(b => b.addEventListener("click", e => {
    e.preventDefault();
    window.scrollTo({ top: 0, behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  }));
})();
