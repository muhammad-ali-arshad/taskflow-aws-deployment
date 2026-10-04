// Sidebar toggle on mobile
document.addEventListener("click", (e) => {
  const t = e.target.closest("[data-toggle-sidebar]");
  if (t) document.querySelector(".sidebar").classList.toggle("open");
});

// Confirm before destructive actions
document.addEventListener("submit", (e) => {
  const msg = e.target.dataset.confirm;
  if (msg && !window.confirm(msg)) e.preventDefault();
});

// Kanban drag & drop -> POST /tasks/<id>/status (JSON)
(function () {
  const board = document.querySelector(".board");
  if (!board) return;
  let dragged = null;

  board.addEventListener("dragstart", (e) => {
    const card = e.target.closest(".kcard");
    if (!card) return;
    dragged = card;
    card.classList.add("dragging");
    e.dataTransfer.effectAllowed = "move";
  });
  board.addEventListener("dragend", () => {
    if (dragged) dragged.classList.remove("dragging");
    board.querySelectorAll(".column").forEach((c) => c.classList.remove("drag-over"));
  });
  board.querySelectorAll(".column").forEach((col) => {
    col.addEventListener("dragover", (e) => { e.preventDefault(); col.classList.add("drag-over"); });
    col.addEventListener("dragleave", () => col.classList.remove("drag-over"));
    col.addEventListener("drop", async (e) => {
      e.preventDefault();
      col.classList.remove("drag-over");
      if (!dragged) return;
      const status = col.dataset.status;
      const from = dragged.closest(".column");
      if (from === col) return;
      col.querySelector(".cards").appendChild(dragged);
      updateCounts();
      try {
        const res = await fetch(`/tasks/${dragged.dataset.id}/status`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status }),
        });
        if (!res.ok) throw new Error();
        const data = await res.json();
        const prog = document.querySelector("[data-progress]");
        if (prog) {
          prog.querySelector("span").style.width = data.progress + "%";
          document.querySelector("[data-progress-label]").textContent = data.progress + "%";
        }
      } catch {
        from.querySelector(".cards").appendChild(dragged);
        updateCounts();
        alert("Could not update the task. Please try again.");
      }
    });
  });
  function updateCounts() {
    board.querySelectorAll(".column").forEach((c) => {
      c.querySelector(".count").textContent = c.querySelectorAll(".kcard").length;
    });
  }
})();
