"""Conclusion Engine — turns triplets + vulnerability findings into a readable narrative."""

from __future__ import annotations


def generate_conclusion(
    triplets: list[dict],
    vulnerability_map: list[dict],
    static_landmarks: list[dict],
    breach_probability: float,
) -> str:
    """
    Synthesize entity triplets and vulnerability findings into a
    concrete, conversational conclusion that reads like a stalker's notes.
    """
    if not triplets and not vulnerability_map and not static_landmarks:
        return "Baseline established. No recurring routine detected yet."

    lines: list[str] = []

    # --- Triplet-based: conversational "here's what we know about you" ---
    for triplet in triplets:
        loc = triplet["location"].title()
        time = triplet["time"]
        day = triplet["day"]
        activity = triplet["activity"]
        count = triplet["entry_count"]

        if day and time and activity:
            lines.append(
                f"You {activity} at {loc} every {day.title()} in the {time}. "
                f"This appeared in {count} of your posts."
            )
        elif time and activity:
            lines.append(
                f"You {activity} at {loc} in the {time} — this shows up "
                f"in {count} of your posts."
            )
        elif day and activity:
            lines.append(
                f"Every {day.title()}, you {activity} at {loc}."
            )
        elif time:
            lines.append(
                f"You're regularly at {loc} in the {time}. "
                f"This showed up in {count} of your posts."
            )
        elif activity:
            lines.append(
                f"You frequently {activity} at {loc}."
            )
        else:
            lines.append(
                f"{loc} keeps showing up in your posts — {count} times so far."
            )

    # --- Static landmarks: "you're always at X" ---
    for lm in static_landmarks:
        if lm["type"] == "street":
            name = lm["value"].title()
            pct = lm["percentage"]
            if pct >= 60:
                lines.append(
                    f"You're always at {name} — it appears in {pct}% of your footprint. "
                    f"This is almost certainly near where you live or work."
                )
            else:
                lines.append(
                    f"{name} appears in {pct}% of your posts. "
                    f"Someone watching you would flag this as a regular stop."
                )
        elif lm["type"] == "coordinates" and lm.get("signal") == "anomalous_disclosure":
            lines.append(
                f"{lm['appearances']} of your photos were taken at locations that don't "
                f"repeat anywhere else in your footprint. Each is low-risk alone -- it's not "
                f"a pattern -- but a single unusual location can still say more than you'd expect."
            )
        elif lm["type"] == "coordinates":
            lines.append(
                f"Your photos keep pinging the same GPS coordinates "
                f"({lm['value']['lat']}, {lm['value']['lon']}). "
                f"That's in {lm['percentage']}% of your footprint."
            )

    # --- Critical vulnerability callouts ---
    critical = [v for v in vulnerability_map if v["severity"] == "critical"]
    for v in critical:
        if v["category"] == "Routine Leak":
            lines.append(v["finding"])

    # --- Fallback when no triplets but we have vulns ---
    if not triplets and vulnerability_map:
        high = [v for v in vulnerability_map if v["severity"] in ("critical", "high")]
        if high:
            lines.append(
                f"We found {len(high)} high-severity pattern(s) in your posts. "
                f"Your digital footprint reveals exploitable routines."
            )

    # --- Bottom-line risk statement ---
    if breach_probability >= 70:
        lines.append(
            f"Bottom line: a stranger could predict where you'll be and when, "
            f"just from your public posts. Exposure score: {breach_probability}%."
        )
    elif breach_probability >= 40:
        lines.append(
            f"Moderate exposure ({breach_probability}%). Several of your posts "
            f"line up enough to sketch a partial routine."
        )

    if not lines:
        return "Baseline established. No recurring routine detected yet."

    return "\n\n".join(lines)
