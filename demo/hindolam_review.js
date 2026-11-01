"use strict";
const $ = id => document.getElementById(id);
let review, answers = {}, storageKey;
function eligible(item) {
  return item.review_status !== "rejected" && (item.kind !== "vocal" || item.swara_only_verified === true);
}
function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
}
function label(item) { return (item.kind === "vocal" ? "V" : "G") + item.id.split("-")[1]; }
function summary() {
  $("summary").value = "Hindolam listening notes\n" + review.items.filter(eligible).map(item => {
    const answer = answers[item.id] || {};
    return label(item) + ": " + (answer.verdict || "No rating") + (answer.comment ? " — " + answer.comment : "");
  }).join("\n");
}
function save() {
  try { localStorage.setItem(storageKey, JSON.stringify(answers)); } catch (_) { /* Feedback still works without storage. */ }
  summary();
}
function player(item, part) {
  const audio = document.createElement("audio");
  audio.controls = true;
  audio.preload = "metadata";
  audio.src = "/review/hindolam/" + item.paths[part];
  audio.setAttribute("aria-label", label(item) + " " + part);
  audio.addEventListener("play", () => document.querySelectorAll("audio").forEach(other => { if (audio !== other) other.pause(); }));
  audio.addEventListener("error", () => { $("error").hidden = false; $("error").textContent = "This phrase could not load. Try another example or check that its audio is installed."; });
  return audio;
}
function card(item) {
  const article = node("article", undefined, "card");
  const heading = node("div", undefined, "card-top");
  heading.append(node("span", label(item), "badge"), node("h3", item.title));
  article.append(heading);
  const split = item.kind === "vocal" ? item.durations.seed : item.seed.length * .32;
  article.append(node("p", "Listen to both halves together · continuation starts at " + split.toFixed(1) + " seconds", "source-time"));
  article.append(player(item, "combined"));
  const details = node("details");
  details.append(node("summary", "Hear the halves separately"));
  for (const part of ["seed", "response"]) {
    details.append(node("p", part === "seed" ? "Opening" : "Continuation"), player(item, part));
    if (item.kind === "symbolic") details.append(node("p", item[part].join("  "), "notes"));
  }
  if (item.kind === "vocal") details.append(node("p", "Source times: " + item.source_seconds.map(t => t.toFixed(2)).join(" → ") + " seconds. These are proposed cuts, not verified tala boundaries.", "muted"));
  article.append(details);
  const fieldset = node("fieldset");
  fieldset.append(node("legend", "How does " + label(item) + " sound?"));
  for (const verdict of ["Good", "Needs adjustment"]) {
    const choice = node("label", undefined, "choice");
    const input = document.createElement("input");
    input.type = "radio"; input.name = item.id; input.value = verdict;
    input.checked = answers[item.id]?.verdict === verdict;
    input.addEventListener("change", () => { answers[item.id] = {...answers[item.id], verdict}; save(); });
    choice.append(input, document.createTextNode(" " + verdict)); fieldset.append(choice);
  }
  article.append(fieldset);
  const commentLabel = node("label", "Optional note", "comment");
  const comment = document.createElement("textarea");
  comment.rows = 2; comment.value = answers[item.id]?.comment || "";
  comment.placeholder = "For example: ending cut too early, or continuation repeats too much";
  comment.addEventListener("input", () => { answers[item.id] = {...answers[item.id], comment: comment.value}; save(); });
  commentLabel.append(comment); article.append(commentLabel);
  return article;
}
$("copy").addEventListener("click", async () => {
  summary();
  try { await navigator.clipboard.writeText($("summary").value); $("copyStatus").textContent = "Listening notes copied."; }
  catch (_) { $("summary").focus(); $("summary").select(); $("copyStatus").textContent = "Select and copy the summary below."; }
});
(async () => {
  try {
    const response = await fetch("/review/hindolam/review.json");
    if (!response.ok) throw new Error("Hindolam phrases are unavailable in this installation. Return to Swaraga to explore Mohanam.");
    review = await response.json();
    storageKey = review.review_id + ":" + review.items.map(i => i.sha256.combined).join(":");
    try { answers = JSON.parse(localStorage.getItem(storageKey) || "{}"); } catch (_) { answers = {}; }
    for (const item of review.items.filter(eligible)) $(item.kind === "vocal" ? "vocalCards" : "symbolicCards").append(card(item));
    summary(); $("copy").disabled = false;
  } catch (error) { $("error").textContent = error.message; $("error").hidden = false; }
  finally { $("loading").hidden = true; }
})();
