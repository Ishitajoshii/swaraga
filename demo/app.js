"use strict";
const $ = id => document.getElementById(id);
let state, kind = "symbolic", renderVersion = 0;
const players = ["seed", "response", "combined"];
const mediaError = () => { $("error").textContent = "This audio is unavailable. Try another phrase or check that the recording is installed."; $("error").hidden = false; };
for (const part of players) {
  const audio = $(part + "Audio");
  audio.addEventListener("play", () => players.forEach(other => { if (other !== part) $(other + "Audio").pause(); }));
  audio.addEventListener("error", mediaError);
}
async function json(url) {
  const result = await fetch(url);
  const value = await result.json();
  if (!result.ok) throw new Error(value.error || "Unable to load Swaraga.");
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
  const a = record.annotation;
  if (a.level === "phrase") {
    notes(part, a[part + "_notation"].split(/\s+/));
    $(part + "Audio").ontimeupdate = null;
    $(part + "Beat").textContent = "Phrase notation · synchronized note and tala highlighting unavailable.";
    return;
  }
  const events = a[part + "_events"];
  notes(part, events);
  const audio = $(part + "Audio");
  audio.ontimeupdate = () => {
    const seconds = audio.currentTime;
    const anchors = a[part + "_beat_map"];
    let elapsed = seconds * a.tempo_bpm / 60;
    if (anchors) {
      const right = anchors.findIndex(point => point.onset > seconds);
      if (right < 0) elapsed = anchors[anchors.length - 1].beat;
      else if (right === 0) elapsed = anchors[0].beat;
      else {
        const left = anchors[right - 1], next = anchors[right];
        elapsed = left.beat + (seconds - left.onset) / (next.onset - left.onset) * (next.beat - left.beat);
      }
    }
    const beat = (a[part + "_start_beat"] + elapsed) % a.beats_per_cycle;
    $(part + "Beat").textContent = `Tala beat ${Math.floor(beat) + 1} / ${a.beats_per_cycle} · ${anchors ? "reviewed beat map" : "manual timing"}`;
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
  const previous = $("seed").value;
  const records = kind === "symbolic" ? state.symbolic : state.recordings.filter(r => prepared ? r.split === "bank" : r.annotation.level !== "phrase").map(r => ({...r, title: r.title + (r.split === "evaluation" ? " [evaluation query]" : "")}));
  options($("seed"), records);
  if (records.some(r => r.id === previous)) $("seed").value = previous;
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
  if (vocal) {
    const preparedCount = state.recordings.filter(r => r.split === "bank").length;
    const timedCount = state.recordings.filter(r => r.annotation.level !== "phrase").length;
    $("recordingStatus").textContent = `${preparedCount} phrase pairs · ${timedCount} openings with timing annotations for response matching.`;
  }
  $("responseControl").hidden = true;
  $("metadata").textContent = "";
  $("modeLabel").textContent = vocal ? "RECORDED VOCAL PHRASES" : "GENERATE A PHRASE";
  $("modeTitle").textContent = vocal ? "Explore the vocal library" : "Find the next phrase";
  $("explanation").textContent = state.text[vocal ? "vocal_explanation" : "symbolic_explanation"];
  $("emptyText").textContent = vocal ? state.text.empty_catalog : "Generated phrases are unavailable. Check playback availability below.";
  $("empty").querySelector("h2").textContent = vocal ? "Your vocal library is empty" : "Phrases unavailable";
  $("disclosure").textContent = vocal ? state.text.limitations : "Instrumental reference tones at Sa = 240 Hz. Notes use equal temperament and uniform timing; vocal expression and gamakas are not reproduced.";
  $("evidence").textContent = vocal ? "Original pairs preserve the recorded continuation. Response matching finds a different phrase with compatible tuning, tempo, and melodic contour." : "Each opening leads to a repeatable eight-note suggestion guided by Mohanam notation and raga constraints. Explore it as a musical starting point.";
  if (vocal && !id && $("vocalMode").value === "retrieval" && state.recordings.length) {
    $("empty").querySelector("h2").textContent = "Matching responses unavailable";
    $("emptyText").textContent = "Response matching requires note and tala timing annotations. Choose Original phrase pair to listen to the available recordings.";
  }
  if (!id) return;
  $("combinedBlock").hidden = false;
  $("responseAudio").hidden = false;
  $("noResponse").hidden = true;
  $("seedBeat").textContent = "";
  $("responseBeat").textContent = "";
  $("seedBadge").textContent = vocal ? "RECORDED" : "SYNTHESIZED";
  $("seedHeading").textContent = vocal ? state.text.seed_label : "Opening phrase";
  $("seedAudio").setAttribute("aria-label", state.text.play_seed);
  $("responseAudio").setAttribute("aria-label", state.text.play_response);
  if (!vocal) {
    const example = state.symbolic.find(r => r.id === id);
    $("metadata").textContent = `${example.raga}\n16 opening notes → 8 generated swaras\nEvenly spaced reference notes`;
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
  const phraseOnly = query.annotation.level === "phrase";
  const tuning = phraseOnly ? `${query.annotation.shruti_label} · phrase-level playback` : `Sa ${query.annotation.tonic_hz} Hz · ${query.annotation.tempo_bpm.toFixed(1)} beats/min${query.annotation.seed_beat_map ? " average" : ""}`;
  $("metadata").textContent = `${query.raga} · ${query.tala}\n${tuning}`;
  if (phraseOnly) $("evidence").textContent = "This pair preserves the original recorded continuation. The displayed notation describes the phrase; exact note timing, octaves, and tala alignment are not verified.";
  setAudio("seed", audioUrl(id, "seed")); timed("seed", query);
  let response = query;
  const prepared = $("vocalMode").value === "prepared";
  $("responseHeading").textContent = prepared ? "Original continuation" : "Matched continuation";
  $("responseBadge").textContent = prepared ? "ORIGINAL PAIR" : "MATCHED";
  try {
    if (!prepared) {
      const ranked = await json("/api/rank?id=" + encodeURIComponent(id));
      if (version !== renderVersion) return;
      const previous = $("response").value;
      options($("response"), ranked.map(r => ({...r, title: r.title})));
      if (ranked.some(r => r.id === previous)) $("response").value = previous;
      if (!ranked.length) {
        notes("response", []);
        $("responseAudio").hidden = true;
        $("combinedBlock").hidden = true;
        $("noResponse").hidden = false;
        $("noResponse").textContent = phraseOnly ? `${query.title} is available as an Original phrase pair. Response matching needs verified note and tala timing for this recording.` : "No matching response is available for this opening. Try another phrase or choose Original phrase pair.";
        return;
      }
      $("responseControl").hidden = false;
      response = state.recordings.find(r => r.id === $("response").value);
    }
    for (const part of ["response", "combined"]) setAudio(part, audioUrl(id, part, response.id));
    timed("response", response);
    if (!phraseOnly) $("evidence").textContent = prepared
      ? "Note and tala highlighting follow the recording’s reviewed timing annotations."
      : "This continuation comes from another recorded exercise with compatible timing, tuning, and contour. Available matches depend on the recordings in the library.";
    $("joinNote").textContent = "Opening and continuation joined at their annotated boundary, with the original voice and timing preserved.";
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
main().catch(error => { $("error").textContent = error.message + " Check that Swaraga is running, then refresh this page."; $("error").hidden = false; });
