"use strict";
const $ = id => document.getElementById(id);
let state, kind = "symbolic", renderVersion = 0;
const players = ["seed", "response", "combined"];
const mediaError = () => { $("error").textContent = "Audio could not be loaded. Check the selected files and restart the local demo."; $("error").hidden = false; };
for (const part of players) {
  const audio = $(part + "Audio");
  audio.addEventListener("play", () => players.forEach(other => { if (other !== part) $(other + "Audio").pause(); }));
  audio.addEventListener("error", mediaError);
}
async function json(url) {
  const result = await fetch(url);
  const value = await result.json();
  if (!result.ok) throw new Error(value.error || "Unable to load the demo.");
  return value;
}
function options(select, records) {
  select.replaceChildren(...records.map(r => new Option(r.title, r.id)));
}
function audioUrl(id, part, response) {
  const params = new URLSearchParams({ kind, id, part, mode: $("vocalMode").value });
  if (response) params.set("response", response);
  return "/api/audio?" + params;
}
function setAudio(part, url) {
  const audio = $(part + "Audio");
  audio.pause();
  audio.ontimeupdate = null;
  audio.removeAttribute("src");
  if (url) audio.src = url;
  audio.load();
}
function noteText(event) {
  if (event.kind === "rest") return "rest";
  return (event.kind === "hold" ? "~" : "") + event.swara + (event.octave > 0 ? "′".repeat(event.octave) : "·".repeat(-event.octave));
}
function notes(part, tokens) {
  $(part + "Notes").replaceChildren(...tokens.map(token => {
    const span = document.createElement("span");
    span.className = "note" + (typeof token === "object" ? " " + token.kind : "");
    span.textContent = typeof token === "object" ? noteText(token) : token;
    return span;
  }));
}
function timed(part, record) {
  const a = record.annotation, events = a[part + "_events"];
  notes(part, events);
  const audio = $(part + "Audio");
  audio.ontimeupdate = () => {
    const seconds = audio.currentTime;
    const beat = (a[part + "_start_beat"] + seconds * a.tempo_bpm / 60) % a.beats_per_cycle;
    $(part + "Beat").textContent = `Tala position ${(beat + 1).toFixed(1)} / ${a.beats_per_cycle} · manual timing`;
    [...$(part + "Notes").children].forEach((node, i) => node.classList.toggle("active", seconds >= events[i].onset && seconds < events[i].onset + events[i].duration));
  };
  audio.ontimeupdate();
}
function selectMode(next) {
  kind = next;
  $("symbolicTab").setAttribute("aria-pressed", String(kind === "symbolic"));
  $("vocalTab").setAttribute("aria-pressed", String(kind === "vocal"));
  $("vocalControls").hidden = kind !== "vocal";
  fillSeeds();
  render();
}
function fillSeeds() {
  const prepared = $("vocalMode").value === "prepared";
  const records = kind === "symbolic" ? state.symbolic : state.recordings.filter(r => !prepared || r.split === "bank").map(r => ({...r, title: r.title + (r.split === "evaluation" ? " [evaluation query]" : "")}));
  options($("seed"), records);
}
async function render() {
  const version = ++renderVersion;
  $("error").hidden = true;
  players.forEach(p => setAudio(p, null));
  const vocal = kind === "vocal", id = $("seed").value;
  $("empty").hidden = !!id;
  $("players").hidden = !id;
  $("seedControl").hidden = !id;
  $("vocalControls").hidden = !vocal || !state.recordings.length;
  $("responseControl").hidden = true;
  $("metadata").textContent = "";
  $("modeLabel").textContent = vocal ? "RECORDED VOCAL PHRASES" : "SYMBOLIC CONTINUATION";
  $("modeTitle").textContent = vocal ? "Continue in your voice" : "Find the next phrase";
  $("explanation").textContent = state.text[vocal ? "vocal_explanation" : "symbolic_explanation"];
  $("emptyText").textContent = vocal ? state.text.empty_catalog : "Symbolic examples are unavailable. See the asset messages below.";
  $("empty").querySelector("h2").textContent = vocal ? "Waiting for your voice" : "Examples unavailable";
  $("disclosure").textContent = vocal ? state.text.limitations : "Synthesized reference tones at Sa = 240 Hz, using equal temperament. No recorded voice or gamakas. Uniform note durations are a playback aid, not a performance transcription.";
  $("evidence").textContent = vocal ? "Prepared mode plays an approved seed/response pair. Retrieval ranks other recorded phrases; it does not compose new vocal audio. Musical quality still needs listening review." : `B1 n-gram baseline · ${state.training.windows} valid overlapping training windows from ${state.training.compositions} compositions. ${state.training.note}`;
  if (!id) return;
  $("combinedBlock").hidden = false;
  $("responseAudio").hidden = false;
  $("noResponse").hidden = true;
  $("seedBeat").textContent = "";
  $("responseBeat").textContent = "";
  $("seedBadge").textContent = vocal ? "OWN RECORDING" : "SYNTHESIZED";
  $("seedHeading").textContent = vocal ? state.text.seed_label : "Practice seed";
  $("seedAudio").setAttribute("aria-label", state.text.play_seed);
  $("responseAudio").setAttribute("aria-label", state.text.play_response);
  if (!vocal) {
    const example = state.symbolic.find(r => r.id === id);
    $("metadata").textContent = `${example.raga} · ${example.tala}\n16 seed positions → 8 generated swaras\nDeterministic n-gram continuation`;
    $("responseHeading").textContent = "Generated continuation";
    $("responseBadge").textContent = "8 SWARAS";
    $("joinNote").textContent = example.timing_note;
    notes("seed", example.tokens); notes("response", example.generated);
    players.forEach(p => setAudio(p, audioUrl(id, p)));
    $("download").href = audioUrl(id, "combined");
    $("download").download = `swaraga-symbolic-${id}.wav`;
    return;
  }
  const query = state.recordings.find(r => r.id === id);
  $("metadata").textContent = `${query.raga} · ${query.tala}\nSa ${query.annotation.tonic_hz} Hz · ${query.annotation.tempo_bpm} beats/min\nSource take: ${query.source_take}`;
  setAudio("seed", audioUrl(id, "seed")); timed("seed", query);
  let response = query;
  const prepared = $("vocalMode").value === "prepared";
  $("responseHeading").textContent = prepared ? "Approved paired response" : "Retrieved recorded response";
  $("responseBadge").textContent = prepared ? "PREPARED PAIR" : "RETRIEVED";
  try {
    if (!prepared) {
      const ranked = await json("/api/rank?id=" + encodeURIComponent(id));
      if (version !== renderVersion) return;
      const previous = $("response").value;
      options($("response"), ranked.map(r => ({...r, title: `${r.title} · distance ${r.score}`})));
      if (ranked.some(r => r.id === previous)) $("response").value = previous;
      if (!ranked.length) {
        notes("response", []);
        $("responseAudio").hidden = true;
        $("combinedBlock").hidden = true;
        $("noResponse").hidden = false;
        $("noResponse").textContent = "No compatible response from another seed family. Try a prepared bank example or add more approved phrases.";
        return;
      }
      $("responseControl").hidden = false;
      response = state.recordings.find(r => r.id === $("response").value);
    }
    for (const part of ["response", "combined"]) setAudio(part, audioUrl(id, part, response.id));
    timed("response", response);
    $("joinNote").textContent = "Original recorded phrases joined at their annotated boundary. No pitch shifting, time stretching, or crossfade.";
    $("download").href = audioUrl(id, "combined", response.id);
    $("download").download = `swaraga-${id}-${response.id}.wav`;
  } catch (error) {
    if (version === renderVersion) { $("error").textContent = error.message; $("error").hidden = false; $("combinedBlock").hidden = true; }
  }
}
async function main() {
  state = await json("/api/state");
  $("subtitle").textContent = state.text.subtitle;
  $("symbolicTab").textContent = state.text.symbolic_mode;
  $("vocalTab").textContent = state.text.vocal_mode;
  $("warningBox").hidden = !state.warnings.length;
  $("warnings").replaceChildren(...state.warnings.map(w => { const li = document.createElement("li"); li.textContent = w; return li; }));
  $("symbolicTab").onclick = () => selectMode("symbolic");
  $("vocalTab").onclick = () => selectMode("vocal");
  $("seed").onchange = () => { $("response").replaceChildren(); render(); };
  $("response").onchange = render;
  $("vocalMode").onchange = () => { fillSeeds(); render(); };
  selectMode("symbolic");
}
main().catch(error => { $("error").textContent = error.message + " Start the demo with python scripts/run_demo.py."; $("error").hidden = false; });
