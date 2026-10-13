// Shared behaviour for every page: back-to-top.
(function () {
  document.querySelectorAll("[data-top]").forEach(b => b.addEventListener("click", e => {
    e.preventDefault();
    window.scrollTo({ top: 0, behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  }));
})();
