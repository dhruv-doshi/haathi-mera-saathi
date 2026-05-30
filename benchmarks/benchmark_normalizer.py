"""V1 vs V1.5 benchmark — Layer 2 (the academic-term normalizer), text-level.

What this measures: the quality of the transcript the mentor brain RECEIVES.
- V1: raw STT output goes straight to the LLM (no correction stage).
- V1.5: the raw STT output is repaired by the normalizer before the LLM.

What this does NOT measure: how often Deepgram actually produces these mishearings
in the first place (that needs real audio — Layer 1 / keyterm boosting), nor the
final spoken answer (V1's prompt also tries to compensate downstream). The
"misheard" strings below are plausible STT errors, used to score the normalizer's
*correction capability* and its *safety* (not corrupting clean/casual speech).

Run:  .venv/bin/python benchmarks/benchmark_normalizer.py
Live normalize calls run only when OPENROUTER_API_KEY is set.
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env.local")

import config  # noqa: E402
import lexicon  # noqa: E402
import normalizer  # noqa: E402

LEXICON = lexicon.all_terms()
PROD_TIMEOUT = config.NORMALIZER_TIMEOUT_S  # the real production fallback budget

# category, misheard (what STT might output), intended, key_terms (must appear)
DATASET = [
    # --- trigonometry ---
    ("trig", "signs theta ka value kya hai", "sin theta ka value kya hai", ["sin"]),
    ("trig", "kos theta plus signs theta", "cos theta plus sin theta", ["cos", "sin"]),
    ("trig", "co sec x ki value nikalo", "cosec x ki value nikalo", ["cosec"]),
    ("trig", "cos theta ka graph banao", "cos theta ka graph banao", ["cos"]),
    ("trig", "sign inverse of half", "sin inverse of half", ["sin"]),
    ("trig", "ten theta equals one", "tan theta equals one", ["tan"]),
    ("trig", "tangent theta kya hota hai", "tangent theta kya hota hai", ["tangent"]),
    ("trig", "signs squared plus kos squared", "sin squared plus cos squared", ["sin", "cos"]),
    ("trig", "cosine rule kab lagta hai", "cosine rule kab lagta hai", ["cosine"]),
    # --- calculus ---
    ("calc", "aukalan kaise karte hain", "avkalan kaise karte hain", ["avkalan"]),
    ("calc", "derivative of x squared", "derivative of x squared", ["derivative"]),
    ("calc", "the narrative of sine x", "the derivative of sin x", ["derivative", "sin"]),
    ("calc", "integration by parts samjhao", "integration by parts samjhao", ["integration"]),
    ("calc", "limit x tends to zero", "limit x tends to zero", ["limit"]),
    ("calc", "samakaran nikalna hai", "samakalan nikalna hai", ["samakalan"]),
    # --- physics (Hindi terms) ---
    ("phys", "lambait kaaran kya hota hai", "lambit karan kya hota hai", ["lambit karan"]),
    ("phys", "tu varan nikalo is body ka", "tvaran nikalo is body ka", ["tvaran"]),
    ("phys", "veg aur tu varan mein difference", "veg aur tvaran mein difference", ["veg", "tvaran"]),
    ("phys", "visth apan kitna hua", "visthapan kitna hua", ["visthapan"]),
    ("phys", "talk on the rod", "torque on the rod", ["torque"]),
    ("phys", "angular velocity kya hai", "angular velocity kya hai", ["angular velocity"]),
    ("phys", "momentum conserve hota hai", "momentum conserve hota hai", ["momentum"]),
    ("phys", "frequency aur emplitude", "frequency aur amplitude", ["amplitude"]),
    # --- chemistry ---
    ("chem", "electro file kya hota hai", "electrophile kya hota hai", ["electrophile"]),
    ("chem", "nucleo filic substitution", "nucleophilic substitution", ["nucleophil"]),
    ("chem", "s n one reaction mechanism", "SN1 reaction mechanism", ["sn1"]),
    ("chem", "SN2 reaction fast hai", "SN2 reaction fast hai", ["sn2"]),
    ("chem", "covalent bond samjhao", "covalent bond samjhao", ["covalent"]),
    ("chem", "mole concept clear karo", "mole concept clear karo", ["mole"]),
    # --- algebra ---
    ("alg", "quadratic equation solve karo", "quadratic equation solve karo", ["quadratic"]),
    ("alg", "the logarithm of hundred", "the logarithm of hundred", ["logarithm"]),
    ("alg", "polynomial ka degree kya hai", "polynomial ka degree kya hai", ["polynomial"]),
    # --- code-mixed full sentences ---
    ("mixed", "sir signs theta ka value kya hota hai thirty degree pe",
     "sir sin theta ka value kya hota hai thirty degree pe", ["sin"]),
    ("mixed", "mujhe co sec aur sec ka difference samajhna hai",
     "mujhe cosec aur sec ka difference samajhna hai", ["cosec", "sec"]),
    ("mixed", "is question mein aukalan use karna padega",
     "is question mein avkalan use karna padega", ["avkalan"]),
    ("mixed", "lambait kaaran wala concept nahi aaya",
     "lambit karan wala concept nahi aaya", ["lambit karan"]),
]

# Casual utterances — the gate must SKIP these (zero LLM cost, zero changes).
CONTROLS = [
    "haan bhai theek hai chalo padhte hain",
    "mujhe neend aa rahi hai yaar",
    "kal ka test kaisa gaya tha",
    "thoda break le lete hain pehle",
    "thank you bhaiya ab samajh aa gaya",
    "main thodi der baad padhunga",
    "aaj mood nahi hai kuch karne ka",
    "mummy bula rahi hai ek minute",
    "ye chapter bohot boring hai",
    "chalo kal milte hain phir",
]


def terms_present(text, key_terms):
    low = text.lower()
    return sum(t.lower() in low for t in key_terms)


async def run():
    llm = config.build_normalizer_llm() if os.environ.get("OPENROUTER_API_KEY") else None
    if llm is None:
        print("OPENROUTER_API_KEY not set — cannot run live normalizer. Aborting.")
        sys.exit(1)

    cats = {}
    total_terms = v1_terms = v15_terms = 0
    gate_academic_hits = 0
    latencies = []
    rows = []

    for cat, misheard, intended, keys in DATASET:
        gated = normalizer.looks_academic(misheard, LEXICON)
        gate_academic_hits += gated

        if gated:
            t0 = time.perf_counter()
            corrected = await normalizer.normalize(misheard, LEXICON, llm, timeout=8.0)
            latencies.append(time.perf_counter() - t0)
        else:
            corrected = misheard  # gate skipped it (a miss for academic content)

        n = len(keys)
        v1 = terms_present(misheard, keys)
        v15 = terms_present(corrected, keys)
        total_terms += n
        v1_terms += v1
        v15_terms += v15

        c = cats.setdefault(cat, [0, 0, 0])
        c[0] += n
        c[1] += v1
        c[2] += v15

        rows.append({"cat": cat, "misheard": misheard, "intended": intended,
                     "corrected": corrected, "keys": keys, "gated": gated,
                     "v1": v1, "v15": v15, "n": n})

    # Controls: gate should skip; if it fires, the normalizer must not change text.
    control_skipped = 0
    control_overcorrected = 0
    for text in CONTROLS:
        if not normalizer.looks_academic(text, LEXICON):
            control_skipped += 1
        else:
            out = await normalizer.normalize(text, LEXICON, llm, timeout=8.0)
            if out.strip() != text.strip():
                control_overcorrected += 1

    # ---- report ----
    print("=" * 64)
    print("V1 vs V1.5 — Layer 2 (normalizer), transcript fidelity")
    print("=" * 64)
    print(f"Academic phrases: {len(DATASET)}   key terms: {total_terms}")
    print()
    print(f"{'Category':10} {'terms':>6} {'V1 recov':>9} {'V1.5 recov':>11}")
    for cat, (n, a, b) in cats.items():
        print(f"{cat:10} {n:>6} {a/n*100:>8.0f}% {b/n*100:>10.0f}%")
    print("-" * 40)
    print(f"{'OVERALL':10} {total_terms:>6} {v1_terms/total_terms*100:>8.0f}% "
          f"{v15_terms/total_terms*100:>10.0f}%")
    print()
    print(f"Term Recovery Rate   V1:   {v1_terms/total_terms*100:.0f}%  "
          f"({v1_terms}/{total_terms})")
    print(f"Term Recovery Rate   V1.5: {v15_terms/total_terms*100:.0f}%  "
          f"({v15_terms}/{total_terms})")
    print(f"Absolute improvement:      +{(v15_terms-v1_terms)/total_terms*100:.0f} "
          f"points  ({v15_terms-v1_terms} more terms recovered)")
    print()
    print(f"Gate recall (academic flagged):  {gate_academic_hits}/{len(DATASET)} "
          f"= {gate_academic_hits/len(DATASET)*100:.0f}%")
    print(f"Gate specificity (casual skipped): {control_skipped}/{len(CONTROLS)} "
          f"= {control_skipped/len(CONTROLS)*100:.0f}%")
    print(f"Over-correction on casual speech:  {control_overcorrected}/{len(CONTROLS)}")
    print()
    if latencies:
        latencies.sort()
        mean = sum(latencies) / len(latencies)
        p50 = latencies[len(latencies) // 2]
        p95 = latencies[int(len(latencies) * 0.95)]
        within = sum(x <= PROD_TIMEOUT for x in latencies)
        print(f"Normalizer latency (n={len(latencies)}): "
              f"mean {mean*1000:.0f}ms  p50 {p50*1000:.0f}ms  p95 {p95*1000:.0f}ms")
        print(f"Within {PROD_TIMEOUT:.1f}s production budget: "
              f"{within}/{len(latencies)} = {within/len(latencies)*100:.0f}%")
    print()

    # show the corrections that mattered
    print("Sample corrections (V1 transcript -> V1.5 transcript):")
    for r in rows:
        if r["v15"] > r["v1"]:
            print(f"  [{r['cat']}] {r['misheard']!r}")
            print(f"        -> {r['corrected']!r}")

    out_path = ROOT / "benchmarks" / "results_layer2.json"
    out_path.write_text(json.dumps({
        "n_phrases": len(DATASET), "total_terms": total_terms,
        "v1_recovery": v1_terms / total_terms, "v15_recovery": v15_terms / total_terms,
        "gate_recall": gate_academic_hits / len(DATASET),
        "gate_specificity": control_skipped / len(CONTROLS),
        "over_correction": control_overcorrected,
        "rows": rows,
    }, indent=2, ensure_ascii=False))
    print(f"\nFull results -> {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    asyncio.run(run())
