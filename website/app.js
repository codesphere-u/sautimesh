/* SautiMesh Interactive & Animated Voice Mesh Controller (0 external dependencies) */
(function () {
  "use strict";

  function showToast(msg) {
    const el = document.getElementById("toast");
    if (!el) return;
    el.textContent = msg;
    el.classList.add("show");
    clearTimeout(el._timer);
    el._timer = setTimeout(() => el.classList.remove("show"), 2200);
  }

  function copyText(text) {
    if (!text) return;
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(() => showToast("Copied command"));
    } else {
      const ta = document.createElement("textarea");
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      ta.remove();
      showToast("Copied command");
    }
  }

  document.addEventListener("click", (e) => {
    const copyBtn = e.target.closest("[data-copy]");
    if (copyBtn) copyText(copyBtn.getAttribute("data-copy"));
  });

  // Pure WebAudio gentle syllable-cadence feedback (zero external audio files needed)
  function playCadenceSound(text) {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return;
    try {
      const ctx = new AudioCtx();
      const words = (text || "sautimesh ready").trim().split(/\s+/).slice(0, 7);
      const now = ctx.currentTime;
      words.forEach((word, i) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = "sine";
        const freq = 220 + ((word.length * 37 + i * 29) % 190);
        const start = now + i * 0.11;
        osc.frequency.setValueAtTime(freq, start);
        gain.gain.setValueAtTime(0.001, start);
        gain.gain.exponentialRampToValueAtTime(0.06, start + 0.02);
        gain.gain.exponentialRampToValueAtTime(0.001, start + 0.09);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(start);
        osc.stop(start + 0.095);
      });
    } catch (_err) {
      /* Ignore autoplay policies gracefully */
    }
  }

  // Sequential Pipeline & Equalizer Animation Runner
  function pulsePipeline(containerId, eqId, playAudioText) {
    const pipe = document.getElementById(containerId);
    const eq = document.getElementById(eqId);
    if (eq) {
      eq.classList.add("playing");
      clearTimeout(eq._stopTimer);
      eq._stopTimer = setTimeout(() => eq.classList.remove("playing"), 1450);
    }
    if (playAudioText) playCadenceSound(playAudioText);
    if (!pipe) return;
    const stages = Array.from(pipe.querySelectorAll(".mesh-stage"));
    stages.forEach((s) => s.classList.remove("active"));
    stages.forEach((stage, idx) => {
      setTimeout(() => {
        stages.forEach((s) => s.classList.remove("active"));
        stage.classList.add("active");
      }, idx * 290);
    });
  }

  // Scroll Reveal + Animated Metric Progress Bars
  const reveals = document.querySelectorAll(".reveal");
  const metricBars = document.querySelectorAll(".metric-bar-fill[data-width]");
  function revealElement(el) {
    el.classList.add("in-view");
  }
  function fillBars() {
    metricBars.forEach((bar) => {
      const target = bar.getAttribute("data-width") || "0%";
      requestAnimationFrame(() => {
        bar.style.width = target;
      });
    });
  }

  if ("IntersectionObserver" in window) {
    const obs = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            revealElement(entry.target);
            obs.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.08 }
    );
    reveals.forEach((el) => obs.observe(el));
    setTimeout(fillBars, 120);
  } else {
    reveals.forEach(revealElement);
    fillBars();
  }

  // Homepage install popover & CTA
  const mainBtn = document.getElementById("cta-main-btn");
  const caretBtn = document.getElementById("cta-caret-btn");
  const popover = document.getElementById("cta-popover");
  const heroCmd = document.getElementById("hero-cmd");
  const popCmdCode = document.getElementById("pop-cmd-code");
  const popCopyBtn = document.getElementById("pop-copy-btn");

  const INSTALL_MODES = {
    cli: "pip install -e git+https://github.com/codesphere-u/sautimesh.git#egg=sautimesh",
    turn: 'sautimesh chat --text "Habari daktari, mtoto ana fever kali leo" --currency KES',
    eval: "sautimesh eval && sautimesh serve --port 8765",
    mcp: "sautimesh mcp",
  };

  if (mainBtn && heroCmd) {
    mainBtn.addEventListener("click", () => copyText(heroCmd.textContent.trim()));
  }
  if (caretBtn && popover) {
    caretBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      const willOpen = !popover.classList.contains("open");
      popover.hidden = !willOpen;
      popover.classList.toggle("open", willOpen);
      caretBtn.setAttribute("aria-expanded", String(willOpen));
    });
    document.addEventListener("click", (e) => {
      if (!popover.contains(e.target) && e.target !== caretBtn) {
        popover.classList.remove("open");
        popover.hidden = true;
        caretBtn.setAttribute("aria-expanded", "false");
      }
    });
  }
  if (popover && popCmdCode) {
    popover.querySelectorAll(".pop-tab[data-persona]").forEach((tab) => {
      tab.addEventListener("click", () => {
        popover.querySelectorAll(".pop-tab").forEach((t) => {
          t.classList.remove("active");
          t.setAttribute("aria-selected", "false");
        });
        tab.classList.add("active");
        tab.setAttribute("aria-selected", "true");
        const cmd = INSTALL_MODES[tab.getAttribute("data-persona")] || INSTALL_MODES.cli;
        popCmdCode.textContent = cmd;
        if (heroCmd) heroCmd.textContent = cmd;
      });
    });
  }
  if (popCopyBtn && popCmdCode) {
    popCopyBtn.addEventListener("click", () => copyText(popCmdCode.textContent.trim()));
  }

  // Homepage Interactive Voice Preview & Equalizer
  const PREVIEW_VIEWS = {
    term: `$ sautimesh chat --text "Habari daktari, mtoto ana fever kali leo" --currency KES

SautiMesh v0.1.0 — Tier: offline_rules (0 ms · 0 cellular bytes · KES 0.0)
  Detected Langs:    sw + en (CSI: 0.429)
  Domain / Intent:   health_triage / pediatric_fever_triage
  SMS Fallback:      GSM-7 · 1 segment (108/160 chars)
  Reply (Swahili):   "Kwa homa ya mtoto, mpime joto leo, mpe maji mengi safi,
                      na umpeleke kliniki kupima malaria kabla ya kumeza dawa."`,
    codeswitch: `$ sautimesh analyze "Nnyamba mangu ssebo omwana avaamu omusaayi PIN: 4829"

  Primary Language:  lg (Luganda) · Urgency: HIGH
  PII Stripped:      ["pin_or_otp"] -> PIN=[REDACTED]
  SMS / USSD Fit:    GSM-7 · 1 SMS segment · 1 USSD page (61/182 chars)
  Escalation Gate:   human_escalation = true (queued offline in SQLite WAL)`,
    dpg: `{
  "schema": "sautimesh.dpg.v1",
  "license": "MIT",
  "benchmark_eval": { "passed": 7, "total": 7, "offline_containment_pct": 100.0 },
  "languages": ["sw", "lg", "yo", "ha", "fr", "en", "pcm", "nyn"],
  "safeguards": {
    "pii_redaction_before_cloud": ["phone_number", "pin_or_otp", "national_id"],
    "currencies": ["UGX", "KES", "NGN", "GHS", "XOF", "ZAR", "RWF", "TZS", "USD"]
  }
}`,
  };

  const previewCode = document.getElementById("home-preview-code");
  const playDemoBtn = document.getElementById("play-demo-btn");
  if (playDemoBtn) {
    playDemoBtn.addEventListener("click", () => {
      pulsePipeline("home-pipeline", "home-eq", "Habari daktari mtoto ana fever");
    });
  }
  document.querySelectorAll(".frame-tab[data-homeview]").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".frame-tab[data-homeview]").forEach((b) => {
        b.classList.remove("active");
        b.setAttribute("aria-selected", "false");
      });
      btn.classList.add("active");
      btn.setAttribute("aria-selected", "true");
      if (previewCode) {
        previewCode.textContent = PREVIEW_VIEWS[btn.getAttribute("data-homeview")] || PREVIEW_VIEWS.term;
      }
      pulsePipeline("home-pipeline", "home-eq", null);
    });
  });

  // Homepage Interactive Language Pill Cloud + Sync Console Output
  const langPreview = document.getElementById("lang-sample-note");
  const LANG_CONSOLE_SAMPLES = {
    sw: `$ sautimesh chat --text "Habari daktari, mtoto ana fever kali leo" --currency KES\n\nSautiMesh v0.1.0 — Tier: offline_rules (0 ms · 0 cellular bytes · KES 0.0)\n  Detected Langs:    sw + en (CSI: 0.429)\n  SMS Fallback:      GSM-7 · 1 segment (108/160 chars)\n  Reply (Swahili):   "Kwa homa ya mtoto, mpime joto leo, mpe maji mengi safi."`,
    lg: `$ sautimesh chat --text "Ssebo obuwuka bungi mu kasooli farm yange" --currency UGX\n\nSautiMesh v0.1.0 — Tier: offline_rules (0 ms · 0 cellular bytes · UGX 0.0)\n  Detected Langs:    lg + en (CSI: 0.333)\n  SMS Fallback:      GSM-7 · 1 segment (92/160 chars)\n  Reply (Luganda):   "Kebera amababi ga kasooli enkya, kozesa evvu oba neem."`,
    yo: `$ sautimesh analyze "Ekaaro omo mi ni iba PIN: 4829"\n\n  Detected Langs:    yo (Yoruba) · Diacritics -> UCS-2\n  PII Scrubbed:      PIN=[REDACTED]\n  USSD Envelope:     END 1 page (70 chars limit respected offline)`,
    ha: `$ sautimesh chat --text "Sannu malam, kwari suna cin masara" --currency NGN\n\nSautiMesh v0.1.0 — Tier: offline_rules (0 ms · 0 cellular bytes · NGN 0.0)\n  Detected Langs:    ha (Hausa) · Domain: agri_extension\n  SMS Fallback:      GSM-7 · 1 segment (96/160 chars)`,
  };
  document.querySelectorAll(".lang-chip[data-lang-note]").forEach((chip) => {
    chip.addEventListener("click", () => {
      document.querySelectorAll(".lang-chip[data-lang-note]").forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      if (langPreview) langPreview.textContent = chip.getAttribute("data-lang-note");
      const m = /\((\w+)\)/.exec(chip.textContent || "");
      const codeKey = m ? m[1] : "";
      if (previewCode && LANG_CONSOLE_SAMPLES[codeKey]) {
        previewCode.textContent = LANG_CONSOLE_SAMPLES[codeKey];
      }
      pulsePipeline("home-pipeline", "home-eq", chip.textContent);
    });
  });

  // Docs chapter switcher & install widget
  const chapters = document.querySelectorAll(".doc-chapter[data-chapter]");
  const navButtons = document.querySelectorAll("[data-doc-target]");
  const titleEl = document.getElementById("doc-chapter-title");
  const prevBtn = document.getElementById("doc-prev-btn");
  const nextBtn = document.getElementById("doc-next-btn");
  const CHAPTER_ORDER = Array.from(chapters).map((c) => ({
    id: c.getAttribute("data-chapter"),
    label: c.getAttribute("data-title") || c.getAttribute("data-chapter"),
  }));

  function activateChapter(targetId) {
    if (!chapters.length) return;
    chapters.forEach((c) => {
      c.hidden = c.getAttribute("data-chapter") !== targetId;
    });
    document.querySelectorAll(".doc-nav-link").forEach((b) => {
      b.classList.toggle("active", b.getAttribute("data-doc-target") === targetId);
    });
    document.querySelectorAll(".docs-mobile-chip").forEach((b) => {
      b.classList.toggle("active", b.getAttribute("data-doc-target") === targetId);
    });
    document.querySelectorAll(".doc-subrail").forEach((sr) => {
      sr.classList.toggle("open", sr.getAttribute("data-subrail") === targetId);
    });
    const idx = CHAPTER_ORDER.findIndex((c) => c.id === targetId);
    if (titleEl && idx >= 0) titleEl.textContent = CHAPTER_ORDER[idx].label;
    if (prevBtn) {
      prevBtn.hidden = idx <= 0;
      if (idx > 0) {
        prevBtn.setAttribute("data-go-chapter", CHAPTER_ORDER[idx - 1].id);
        prevBtn.querySelector("strong").textContent = "← " + CHAPTER_ORDER[idx - 1].label;
      }
    }
    if (nextBtn) {
      nextBtn.hidden = idx < 0 || idx >= CHAPTER_ORDER.length - 1;
      if (idx >= 0 && idx < CHAPTER_ORDER.length - 1) {
        nextBtn.setAttribute("data-go-chapter", CHAPTER_ORDER[idx + 1].id);
        nextBtn.querySelector("strong").textContent = CHAPTER_ORDER[idx + 1].label + " →";
      }
    }
  }

  navButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      activateChapter(btn.getAttribute("data-doc-target"));
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  });
  document.querySelectorAll("[data-doc-anchor]").forEach((a) => {
    a.addEventListener("click", () => {
      activateChapter(a.getAttribute("data-doc-anchor"));
    });
  });
  [prevBtn, nextBtn].forEach((b) => {
    if (!b) return;
    b.addEventListener("click", () => {
      const target = b.getAttribute("data-go-chapter");
      if (target) {
        activateChapter(target);
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
    });
  });

  const DOC_INSTALL_TABS = {
    pip: {
      eyebrow: "Install Python Package (3.11+)",
      cmd: "pip install -e git+https://github.com/codesphere-u/sautimesh.git#egg=sautimesh",
      helper: "Runs 100% offline on Python 3.11+ stdlib across Linux, macOS, Raspberry Pi & Android Termux.",
    },
    voice: {
      eyebrow: "Optional Offline Whisper / Piper Weights",
      cmd: "pip install -e '.[voice]' && sautimesh doctor",
      helper: "Wires local faster-whisper, whisper.cpp, Sunbird Sunflower v2, or Piper ONNX TTS adapters.",
    },
    mcp: {
      eyebrow: "Claude Code / Cursor / Antigravity MCP",
      cmd: "sautimesh mcp",
      helper: "Starts the zero-dependency stdio JSON-RPC 2.0 MCP server with 5 native multilingual voice tools.",
    },
    workbench: {
      eyebrow: "Local Voice Workbench Server",
      cmd: "sautimesh serve --port 8765",
      helper: "Opens interactive local API (/api/turn, /api/eval, /api/queue, /api/dpg) and SQLite WAL outbox.",
    },
  };

  document.querySelectorAll("[data-installtab]").forEach((tab) => {
    tab.addEventListener("click", () => {
      const key = tab.getAttribute("data-installtab");
      const spec = DOC_INSTALL_TABS[key];
      if (!spec) return;
      document.querySelectorAll("[data-installtab]").forEach((t) => {
        t.classList.remove("active");
        t.setAttribute("aria-selected", "false");
      });
      tab.classList.add("active");
      tab.setAttribute("aria-selected", "true");
      const eb = document.getElementById("install-eyebrow");
      const pre = document.getElementById("install-cmd-pre");
      const helper = document.getElementById("install-helper");
      const cbtn = document.getElementById("install-copy-btn");
      if (eb) eb.textContent = spec.eyebrow;
      if (pre) pre.textContent = spec.cmd;
      if (helper) helper.textContent = spec.helper;
      if (cbtn) cbtn.setAttribute("data-copy", spec.cmd);
    });
  });

  // Animated Studio Simulator (studio.html)
  const studioInput = document.getElementById("studio-utterance");
  const studioCurrency = document.getElementById("studio-currency");
  const studioBtn = document.getElementById("studio-run-btn");
  const studioAudioBtn = document.getElementById("studio-audio-btn");
  const tokenStreamEl = document.getElementById("studio-token-stream");

  if (studioInput && studioBtn) {
    const LEX = {
      sw: { habari: "hello", mtoto: "child", homa: "fever", kliniki: "clinic", dawa: "medicine", wadudu: "pests", mahindi: "maize", fedha: "money", salio: "balance", haraka: "urgent" },
      lg: { ssebo: "sir", nnyamba: "help me", omwana: "child", omusujja: "fever", eddwaliro: "hospital", obuwuka: "pests", kasooli: "maize", omusaayi: "bleeding", mangu: "urgent", ssente: "money" },
      yo: { bawo: "how", omo: "child", iba: "fever", ileiwosan: "clinic", oogun: "medicine", kokoro: "pests", agbado: "maize", ejo: "please", owo: "money" },
      ha: { sannu: "hello", yaro: "child", zazzabi: "fever", asibiti: "clinic", kwari: "pests", masara: "maize", gaggawa: "urgent", kudi: "money" },
      fr: { bonjour: "hello", enfant: "child", fievre: "fever", urgence: "urgent", saignement: "bleeding", clinique: "clinic", mais: "maize" },
    };
    const REPLIES = {
      "health_triage:emergency_referral": {
        sw: "Hatari kubwa: Tafadhali mpeleke mgonjwa kliniki iliyo karibu haraka sana.",
        lg: "Obulabe obw'amangu: Twala omulwadde mu eddwaliro erisinga okubeera okumpi mangu ddala.",
        fr: "Urgence medicale: veuillez conduire le patient a la clinique la plus proche immediatement.",
        en: "Urgent alert: Please take the patient to the nearest clinic or health post immediately.",
      },
      "health_triage:pediatric_fever_triage": {
        sw: "Kwa homa ya mtoto, mpime joto leo, mpe maji mengi safi, na umpeleke kliniki kupima malaria.",
        lg: "Ku musujja gw'omwana, mupime ebbugumu leero, muwe amazzi amayonjo, omutwale mu eddwaliro.",
        yo: "Fun iba omo, se ayewo igbona ara oni, fun ni omi mimu, ki o mu lo si ile-iwosan.",
        ha: "Game da zazzabin yaro, a duba zafin jiki yau, a ba shi ruwa mai tsafta, a kai shi asibiti.",
        en: "For child fever triage, check temperature today, hydrate with clean fluids, and test for malaria at a clinic.",
      },
      "agri_extension:pest_and_disease_advisory": {
        sw: "Kwa wadudu wa mahindi, kagua majani asubuhi na wasiliana na afisa kilimo.",
        lg: "Ku buwuka mu kasooli, kebera ebikoola ku makya era weebuuze ku mulambuzi w'ebyobulimi.",
        ha: "Game da kwari a gonar masara, a duba ganyaye da sassafe sannan a tuntubi jami'in gona.",
        en: "Inspect maize whorls early morning, remove damaged leaves, and confirm biological control locally.",
      },
      "fintech_momo:wallet_balance_check": {
        sw: "Kwa usalama wa fedha zako, usitaje PIN kwa sauti. Tumia USSD rasmi kuangalia salio.",
        lg: "Olw'obukuumi bwa ssente zo, toyogera PIN mu ddoboozi. Kozesa USSD okukebera ssente.",
        en: "Never speak your PIN aloud. Dial your mobile money official USSD menu offline.",
      },
    };

    function runStudioSimulation(withSound) {
      const raw = studioInput.value.trim();
      const currency = studioCurrency ? studioCurrency.value : "UGX";
      const tokens = raw.split(/\s+/).filter(Boolean);
      const langs = [];
      const norms = [];
      let prevLang = null;
      let switches = 0;

      if (tokenStreamEl) tokenStreamEl.textContent = "";

      tokens.forEach((tok, idx) => {
        const clean = tok.toLowerCase().replace(/^[^\w]+|[^\w]+$/g, "");
        const isPinOrPhone = /^\d{4,6}$/.test(clean) || /\+?\d{9,13}/.test(tok);
        let found = "en";
        let norm = clean;
        for (const [code, map] of Object.entries(LEX)) {
          if (map[clean]) {
            found = code;
            norm = map[clean];
            break;
          }
        }
        if (prevLang && found !== prevLang) switches += 1;
        prevLang = found;
        if (!langs.includes(found) && !isPinOrPhone) langs.push(found);
        norms.push(norm);

        if (tokenStreamEl) {
          const pill = document.createElement("span");
          pill.className = "tok-pill " + (isPinOrPhone ? "tok-pii" : found !== "en" ? "tok-local" : "");
          pill.style.animationDelay = Math.min(idx * 35, 350) + "ms";
          const wordText = document.createTextNode((isPinOrPhone ? "[REDACTED]" : tok) + " ");
          const tag = document.createElement("em");
          tag.textContent = isPinOrPhone ? "pii" : found;
          pill.appendChild(wordText);
          pill.appendChild(tag);
          tokenStreamEl.appendChild(pill);
        }
      });

      const primary = langs[0] || "en";
      const csi = tokens.length > 1 ? (switches / (tokens.length - 1)).toFixed(2) : "0.00";
      const hasUrgent = /\b(urgent|bleeding|haraka|mangu|gaggawa|urgence|saignement|okufa)\b/i.test(norms.join(" ") + " " + raw);
      let key = "health_triage:pediatric_fever_triage";
      if (hasUrgent) key = "health_triage:emergency_referral";
      else if (norms.some((w) => ["pests", "maize"].includes(w))) key = "agri_extension:pest_and_disease_advisory";
      else if (norms.some((w) => ["money", "balance"].includes(w))) key = "fintech_momo:wallet_balance_check";

      const piiRedacted = raw.replace(/\b(pin|otp)\s*[:=#]?\s*\d{4,6}\b/gi, "$1=[REDACTED]").replace(/\+?\d{9,13}/g, "[PHONE]");
      const replySet = REPLIES[key];
      const spoken = replySet[primary] || replySet.en;
      const isAscii = /^[\x20-\x7E\s]+$/.test(spoken);
      const enc = isAscii ? "GSM-7" : "UCS-2";

      document.getElementById("st-lang").textContent = (langs.length ? langs : ["en"]).join(" + ");
      document.getElementById("st-csi").textContent = csi;
      document.getElementById("st-tier").textContent = "offline_rules";
      document.getElementById("st-enc").textContent = enc;
      document.getElementById("st-cost").textContent = currency + " 0.00";
      document.getElementById("st-diag").textContent =
        "Primary: " + primary.toUpperCase() +
        " | Redacted: " + piiRedacted +
        " | Human Escalation: " + (hasUrgent ? "TRUE (Outbox Queued)" : "false");
      document.getElementById("st-json").textContent = JSON.stringify(
        {
          spoken_reply: spoken,
          sms_fallback: spoken.slice(0, 156),
          ussd_preview: "END " + spoken.slice(0, 174),
          offline_contained: true,
          cellular_bytes_used: 0,
        },
        null,
        2
      );

      pulsePipeline("studio-pipeline", "studio-eq", withSound ? spoken : null);
    }

    studioBtn.addEventListener("click", () => runStudioSimulation(false));
    if (studioAudioBtn) {
      studioAudioBtn.addEventListener("click", () => runStudioSimulation(true));
    }
    document.querySelectorAll(".chip-btn[data-sample]").forEach((chip) => {
      chip.addEventListener("click", () => {
        document.querySelectorAll(".chip-btn[data-sample]").forEach((c) => c.classList.remove("active"));
        chip.classList.add("active");
        studioInput.value = chip.getAttribute("data-sample");
        runStudioSimulation(false);
      });
    });
    runStudioSimulation(false);
  }

  // Filterable tables across rules.html & proof.html
  const rulesSearch = document.getElementById("rules-search");
  const rulesLang = document.getElementById("rules-lang");
  const rulesRows = document.querySelectorAll("tbody tr[data-lang]");
  function filterRules() {
    if (!rulesRows.length) return;
    const q = (rulesSearch ? rulesSearch.value : "").trim().toLowerCase();
    const l = rulesLang ? rulesLang.value : "all";
    rulesRows.forEach((tr) => {
      const text = tr.textContent.toLowerCase();
      const lang = tr.getAttribute("data-lang");
      const match = (l === "all" || lang === l) && (!q || text.includes(q));
      tr.style.display = match ? "" : "none";
    });
  }
  if (rulesSearch) rulesSearch.addEventListener("input", filterRules);
  if (rulesLang) rulesLang.addEventListener("change", filterRules);

  document.querySelectorAll(".chip-btn[data-proof-filter]").forEach((chip) => {
    chip.addEventListener("click", () => {
      document.querySelectorAll(".chip-btn[data-proof-filter]").forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      const target = chip.getAttribute("data-proof-filter");
      document.querySelectorAll("tbody tr[data-proof-cat]").forEach((row) => {
        const cat = row.getAttribute("data-proof-cat");
        row.style.display = target === "all" || cat === target ? "" : "none";
      });
    });
  });
})();
