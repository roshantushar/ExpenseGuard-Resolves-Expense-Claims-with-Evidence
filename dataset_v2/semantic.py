"""ExpenseGuard V2 (semantic edition) - semantic layer.
The reference engine still derives every label from the exact structured facts (the *hidden form*). The visible claim no longer exposes them: the published form is empty and the facts
live only in an LLM-drafted employee note. Each note is validated by an independent extraction pass (blind to the hidden facts) and by a re-run of the reference engine on the visible text."""
from __future__ import annotations
import json, random, re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from . import world as W, engine

MANUAL_OK = {"@K010": ("attendees_total must not be recoverable", "Reviewed by hand: the note explicitly says the total headcount was not recorded; the extractor summed the named guests and the host, which the note does not state."),
             "@K151": ("attendees_total should be 20", "Reviewed by hand: the note gives the host, nine colleagues and ten external delegates, which is twenty; the extractor omitted the host."),
             "@K127": ("attendees_total should be 10", "Reviewed by hand: the note gives the host, four colleagues and five external guests (a self-correction from four to five), which is ten; the extractor kept the corrected-away figure.")}
CACHE = Path(__file__).resolve().parent / "semantic_cache.json"
MODEL = "openai/gpt-4o-mini"
BUDGET_USD = 0.50
KIND = {"MEAL_CLIENT": "a meal hosted for external guests", "MEAL_EMPLOYEE": "a meal for employees only", "HOTEL": "hotel accommodation", "AIRFARE": "an airfare purchase", "GROUND_TRANSPORT": "a taxi or ride-hail trip",
        "GIFT": "a gift bought for someone outside the company", "SOFTWARE": "a software subscription", "EQUIPMENT": "an equipment purchase", "TELECOM": "a mobile phone / data plan charge", "TRAINING": "an external training course",
        "CONFERENCE_FEE": "a conference registration fee", "MILEAGE": "use of the employee's own car for business", "CAR_RENTAL": "a rented car", "OTHER": "a charge described in the background note", "ENTERTAINMENT": "external entertainment"}
ENUM = {"cabin": {"ECONOMY": "economy class", "PREMIUM_ECONOMY": "premium economy", "BUSINESS": "business class"},
        "gift_form": {"ITEM": "a physical item handed over to keep", "CASH_EQUIVALENT": "a stored-value gift card, prepaid e-voucher or redeemable code (never use the word cash)"},
        "recipient_type": {"COMMERCIAL": "a private company", "GOVERNMENT": "a state-owned or statutory public body (make the public-sector nature clear WITHOUT using the word government or public official)"},
        "origin_type": {"HOME": "home", "OFFICE": "the employee's usual office", "CLIENT_SITE": "a client's premises", "AIRPORT": "an airport", "OTHER": "another place"},
        "destination_type": {"HOME": "home", "OFFICE": "the employee's usual office", "CLIENT_SITE": "a client's premises", "AIRPORT": "an airport", "OTHER": "another place"},
        "billing": {"MONTHLY": "billed month by month", "ANNUAL_PREPAID": "an annual plan paid up front for the whole year"},
        "charge_to": {"COST_CENTRE": "charged to the employee's department cost centre", "PROJECT": "charged to the project budget"}}
HUMAN = dict(attendees_total="total number of people at the table, employees included", external_attendees="number of external guests among them", external_names="names or organisation of the external guests",
             alcohol_amount="amount of the bill that was alcohol", tip_amount="voluntary tip / gratuity included in the bill", nights="number of nights stayed", conference_ref="conference reference the employee quotes",
             exception_ref="exception reference the employee quotes", business_owner="named business owner of the subscription", item="what was bought", flight_hours="scheduled flight time in hours",
             booked_date="date the ticket was booked", departure_date="departure date", distance_km="distance driven in km", billing_month="month the phone bill covers", learning_plan_id="learning plan identifier",
             provider="training provider", recipient_name="gift recipient's name", recipient_org="gift recipient's organisation", origin="trip origin", destination="trip destination",
             departure_time="time of departure (24h)", activity_end_time="time the business activity ended (24h)", cabin="cabin", gift_form="what the gift is", recipient_type="what kind of organisation received the gift",
             origin_type="where the trip started", destination_type="where the trip ended", billing="billing pattern", charge_to="how the cost is charged", city="city")
SKIP = {"expense_type", "approval_ref"}
STYLES = {
    "indirect": "Everyday wording. Give counts and quantities in words or relations (e.g. 'six of us, two from their side'), never as a field list. 2-4 sentences.",
    "terse": "Very short, shorthand a busy person types on a phone (abbreviations like 'pax', 'biz', 'approx', 'w/'), one or two short sentences, at most 30 words. Minor casual spelling is fine, but every required number stays exact.",
    "verbose": "3-5 sentences with plausible surrounding detail (what the meeting was about, who booked it, how the day went). Include ONE irrelevant number (a room number, a clock time of the meeting, a count of unrelated documents) that a careless reader could confuse with a required fact, while keeping every required fact exact and unambiguous.",
    "secondhand": "Written by an executive assistant on behalf of the employee, formal and slightly indirect ('Please find the receipt for...'), 2-4 sentences.",
    "dictated": "Transcribed from a voice memo: loose punctuation, lower case, filler words ('um', 'so', 'you know'), run-on sentences, and spoken forms for identifiers and numbers (write an identifier like EXC-0003 as 'e x c zero zero zero three', LP-6850 as 'l p six eight five zero'), 2-4 sentences.",
    "local": "Write the note mainly in the local language of the claim (see LOCAL below), keeping merchant, organisation and person names, identifiers and numbers exactly as given; a short English phrase is fine.",
    "challenge": "Written independently by a finance contact in careful third-person memo style ('The employee hosted...'), 2-3 sentences, precise and formal; no shorthand.",
    "mixed": "Everyday wording that includes one or two short local-language words or a local term written in Latin letters (e.g. 'settai', 'nomikai', 'chai', 'dhaba', 'kaigi', 'bhaiya') where natural, 2-4 sentences.",
}
FORBID = re.compile(r"\b([A-Z]{2,5}-\d|approv\w*|reject\w*|escalat\w*|complian\w*|within (the |our )?(limit|ceiling|policy|budget)|exceed\w*|policy|allowed|permitted|reimburs\w*)\b", re.I)
SYSTEM_DRAFT = ("You write the free-text note that an employee (or their assistant) attaches to an expense claim at a company. You receive a FACT SHEET listing what is true about the expense. "
                "Write ONE note in the requested STYLE so that a careful reader can recover every REQUIRED fact exactly, and cannot learn anything listed under ABSENT. Rules: "
                "(1) natural everyday language; never use field names, underscores, ALL-CAPS labels or JSON; "
                "(2) state numbers, dates, times, names, organisations and identifiers exactly as given (numbers may be spelled out); "
                "(3) never state or hint at a conclusion or rule: no words like approved, rejected, exceeds, within limit, policy, allowed, compliant, reimbursable; never mention approvals, sign-offs or exceptions status; "
                "(4) never mention or imply any fact under ABSENT (do not name guests or organisations, do not give counts, do not name the route etc. when they are ABSENT); "
                "(5) the bill total and the transaction date are attached separately, so do not restate them; you may say a detail was not noted (e.g. 'I have not got the headcount') but never give it; "
                "(5b) where it reads naturally you may express derived facts indirectly, and the reader must be able to compute them exactly: nights as check-in and check-out dates, headcount as a list of who was there, alcohol as bottles times unit price, "
                "a cabin by its features (lie-flat seat = business class; extra-legroom seat with upgraded service = premium economy; standard seat = economy); "
                "(5c) spread the required facts across different sentences, use pronouns and back-references, and avoid field-like keywords ('nights', 'pax', 'total'); "
                "(6) keep merchant, organisation and person names exactly as given; "
                'Return ONLY JSON: {"note": "..."}.')
GLOSSARY = ("Policy definitions to apply when extracting: an EXTERNAL attendee is anyone not on the payroll of the company or its subsidiaries (contractors, freelancers, agency staff, partner or customer staff are external; interns and secondees on payroll are employees). "
            "A gift RECIPIENT is GOVERNMENT if it is a ministry, agency, statutory board, authority, municipal or regional body, public university or hospital, or a company owned or controlled by the state, otherwise COMMERCIAL. "
            "If the note corrects itself, use the final corrected value; ignore figures that belong to other occasions (earlier trips, other dinners, last year). Flight duration = landing clock time minus departure clock time (same timezone). Distance = end odometer minus start odometer. Departure date = booking date plus the stated number of days. Alcohol amount = bottles times unit price. "
            "Cabin: a lie-flat seat is BUSINESS, an extra-legroom seat with upgraded service is PREMIUM_ECONOMY, a standard seat is ECONOMY. Nights = check-out date minus check-in date. Do NOT add numbers of people together unless the note itself gives the total headcount or a list of everyone present. "
            "charge_to is PROJECT only if the note says the cost goes to a project budget, otherwise COST_CENTRE. A gift_form is CASH_EQUIVALENT if it is a gift card, prepaid card, e-voucher, redeemable code, store credit or anything exchangeable for money, otherwise ITEM.")
SCHEMA = ("expense_type (MEAL_CLIENT|MEAL_EMPLOYEE|HOTEL|AIRFARE|GROUND_TRANSPORT|GIFT|SOFTWARE|EQUIPMENT|TELECOM|TRAINING|CONFERENCE_FEE|MILEAGE|CAR_RENTAL|OTHER), attendees_total (int), external_attendees (int), external_names (string), "
          "alcohol_amount (number), tip_amount (number), nights (int), conference_ref (string), exception_ref (string), business_owner (string), billing (MONTHLY|ANNUAL_PREPAID), item (string), cabin (ECONOMY|PREMIUM_ECONOMY|BUSINESS), "
          "flight_hours (number), booked_date (YYYY-MM-DD), departure_date (YYYY-MM-DD), distance_km (number), billing_month (YYYY-MM), learning_plan_id (string), provider (string), recipient_name (string), recipient_org (string), "
          "recipient_type (COMMERCIAL|GOVERNMENT), gift_form (ITEM|CASH_EQUIVALENT), origin (string), destination (string), origin_type (HOME|OFFICE|CLIENT_SITE|AIRPORT|OTHER), destination_type (same), departure_time (HH:MM), "
          "activity_end_time (HH:MM), charge_to (COST_CENTRE|PROJECT)")
SYSTEM_EXTRACT = ("You are a claims analyst reading an expense claim. Extract structured facts from the bill summary and the employee note. Use null for every fact that is not stated or cannot be determined from the note; never guess and never infer "
                  "from typical patterns. Dates: the note may give dates informally; convert to ISO using the transaction year unless the note says otherwise. " + GLOSSARY + " Identifiers (conference_ref, exception_ref, learning_plan_id) must be returned in canonical form such as CONF-008, EXC-0003, LP-6850 even if the note spells them out or dictates them. The note may be in Japanese or Hinglish; read it in that language. Return ONLY a JSON object with exactly these keys: " + SCHEMA + ".")


LOCAL = {"JP": "natural business Japanese", "IN": "romanised Hindi mixed with English (Hinglish)"}
COARSE = {"HOTEL": "TRAVEL", "AIRLINE": "TRAVEL", "RIDE_HAIL": "TRAVEL", "CAR_RENTAL": "TRAVEL", "MILEAGE": "TRAVEL", "RESTAURANT": "FOOD_AND_DRINK", "SOFTWARE": "TECH_AND_SUPPLIES", "EQUIPMENT": "TECH_AND_SUPPLIES",
          "TELECOM": "TECH_AND_SUPPLIES", "TRAINING_PROVIDER": "EDUCATION_AND_EVENTS", "CONFERENCE_ORGANISER": "EDUCATION_AND_EVENTS", "GIFT_RETAIL": "RETAIL"}


def fact_sheet(c, flavor):
    f, b = c["_hidden_form"], c["bill"]; et = f["expense_type"]; req, absent = [], []
    if c["_arch"] != "A9":
        req.append(f"expense kind: {KIND[et]}")
    req.append(f"vendor on the bill: {b['merchant']} ({b['city']}, {b['country']}); currency {b['currency']}")
    dv = c.get("_derive") or {}
    for line in dv.get("lines", []):
        req.append(line)
    for k, v in f.items():
        if k in SKIP or k in ("city", "charge_to") or k in dv.get("skip", ()):
            continue
        if v in (None, ""):
            absent.append(HUMAN.get(k, k)); continue
        if k in ENUM:
            v = ENUM[k][v]
        if k in ("alcohol_amount", "tip_amount") and not v:
            req.append(f"no {HUMAN[k].split(' ')[0] if k == 'tip_amount' else 'alcohol'} on the bill"); continue
        req.append(f"{HUMAN.get(k, k)}: {v}" + (" (quote exactly, verbatim)" if k in ("recipient_org", "recipient_name", "external_names", "business_owner", "provider") else ""))
    if f.get("charge_to") == "PROJECT":
        req.append(f"the cost is charged to the budget of project {c['project_id']} (say so and quote the project id)")
    if c["_arch"] == "A9":
        return "REQUIRED FACTS:\n- vendor on the bill: %s\n- write only about what the BACKGROUND describes; do not mention what kind of service the bill vendor provides" % b["merchant"]
    if f.get("external_attendees") == 0 and f.get("attendees_total"):
        req.append("all attendees are employees (external guests: none)")
    if flavor:
        req.append(flavor)
    for nz in c.get("_noise", []):
        req.append("STYLE REQUIREMENT: " + nz)
    return "REQUIRED FACTS:\n- " + "\n- ".join(req) + ("\nABSENT (never mention or imply):\n- " + "\n- ".join(absent) if absent else "")


def flavor_for(c, rng):
    f = c["_hidden_form"]
    if f["expense_type"] == "MEAL_EMPLOYEE" and (f.get("attendees_total") or 0) >= 3 and rng.random() < 0.9:
        return "make it clear that some of the employees come from a subsidiary or another office of the company or are interns on payroll (they are still employees)"
    if f["expense_type"] == "MEAL_CLIENT" and (f.get("external_attendees") or 0) >= 1 and f.get("external_names") and rng.random() < 0.85:
        return "describe at least one external guest as a freelance consultant, contractor or agency staff working with the team (still external), keeping the names exactly as given"
    return ""


def derive_for(c, rng):
    """Indirect (computed) expression of facts: the reader must calculate them exactly."""
    f = c["_hidden_form"]; d = dict(skip=set(), lines=[]); et = f["expense_type"]
    if et == "HOTEL" and f.get("nights") and rng.random() < 0.9:
        out = c["transaction_date"]; inn = W.date.fromisoformat(out) - W.timedelta(days=int(f["nights"]))
        d["skip"].add("nights"); d["lines"].append(f"stay expressed ONLY as check-in date {inn.isoformat()} and check-out date {out} (do NOT state the number of nights; the note MUST give both dates)")
    if et in ("MEAL_CLIENT", "MEAL_EMPLOYEE") and (f.get("attendees_total") or 0) >= 2 and rng.random() < 0.85:
        n, e = int(f["attendees_total"]), int(f.get("external_attendees") or 0)
        d["skip"].add("attendees_total"); d["lines"].append(f"who was present, expressed ONLY as a list (do NOT state a total; the list MUST include the employee themself as the first person): the employee, {n - e - 1} colleague(s) of the employee" + (f", and {e} external guest(s)" if e else ""))
    if et in ("MEAL_CLIENT", "MEAL_EMPLOYEE") and (f.get("alcohol_amount") or 0) > 0 and rng.random() < 0.9:
        a = float(f["alcohol_amount"]); k = 2 if a % 2 == 0 else 1
        d["skip"].add("alcohol_amount"); d["lines"].append(f"alcohol expressed ONLY as {k} bottle(s) at {a / k:g} each (do NOT state the total alcohol amount)")
    if et == "AIRFARE" and f.get("flight_hours") and rng.random() < 0.8:
        h = float(f["flight_hours"]); dep = rng.choice([7, 8, 9, 10, 11, 12]) * 60 + rng.choice([0, 15, 30, 45]); arr = dep + int(round(h * 60))
        hm = lambda m: f"{m // 60:02d}:{m % 60:02d}"
        d["skip"].add("flight_hours"); d["lines"].append(f"flight time expressed ONLY through clock times in the same timezone: departs {hm(dep)}, lands {hm(arr)} (do NOT state the duration)")
    if et == "AIRFARE" and f.get("booked_date") and f.get("departure_date") and rng.random() < 0.7:
        n = W.days_between(f["booked_date"], f["departure_date"])
        d["skip"].add("departure_date"); d["lines"].append(f"departure date expressed ONLY as {n} days after the booking date (state the booking date {f['booked_date']} normally; the note MUST say how many days later the flight departs; do NOT state the departure date itself)")
    if et == "MILEAGE" and f.get("distance_km") and rng.random() < 0.85:
        st_ = rng.randint(10000, 60000)
        d["skip"].add("distance_km"); d["lines"].append(f"distance expressed ONLY through odometer readings: {st_} at the start and {st_ + int(f['distance_km'])} at the end (do NOT state the distance)")
    return d


def noise_for(c, rng):
    """Distractors and messiness that keep the true facts exact: an irrelevant figure about another occasion, a self-correction, or a relayed fact."""
    f = c["_hidden_form"]; et = f["expense_type"]; out = []
    numeric = et in ("HOTEL", "MEAL_CLIENT", "MEAL_EMPLOYEE", "AIRFARE", "MILEAGE", "GROUND_TRANSPORT")
    if numeric and rng.random() < 0.55:
        out.append("include ONE clearly labelled figure about a DIFFERENT occasion of the same kind (an earlier trip's stay length, last year's cabin, another dinner's headcount) that a careless reader could mix up; make it unambiguous that it is not part of this claim")
    if numeric and rng.random() < 0.35:
        out.append("include a brief self-correction of ONE required numeric fact: first say a wrong value, then correct it to the true value, so the final stated value is the true one")
    if numeric and rng.random() < 0.3:
        out.append("say that a colleague told you ONE of the required facts (e.g. 'Ravi mentioned...'), keeping the value exact")
    return out


def draft_prompt(c, style, flavor, fb, explicit=False):
    bg = c["_orig_desc"]
    if c["_arch"] == "A9":
        bg_line = "BACKGROUND (the employee's note describes a DIFFERENT kind of expense than the bill; base the note on this and preserve that mismatch, do not reconcile it): " + bg
    else:
        bg_line = "BACKGROUND (an earlier short note; reuse its event, vendor and organisation names but never any fact under ABSENT): " + bg
    if style == "local":
        reg = W.COUNTRY_TO_REGION[c["bill"]["country"]]; user_style = STYLES["local"] + f" LOCAL = {LOCAL.get(reg, 'English')}."
    else:
        user_style = STYLES[style]
    user = f"STYLE: {user_style}\n\n{fact_sheet(c, flavor)}\n\n{bg_line}"
    if fb:
        user += "\n\nYOUR PREVIOUS ATTEMPT FAILED VALIDATION: " + fb + " Fix this."
    if explicit:
        must = [HUMAN[k] for k in ("attendees_total", "external_names", "origin", "destination", "recipient_org", "recipient_name", "distance_km", "learning_plan_id", "business_owner", "nights") if c["_hidden_form"].get(k) in (None, "") and k in c["_hidden_form"] and not (k == "external_names" and c["_hidden_form"]["expense_type"] != "MEAL_CLIENT")]
        if must:
            user += "\n\nSay plainly, in one short natural clause, that these were not recorded (and nothing else was left out): " + "; ".join(must) + "."
    return user


def call(model, system, user, temperature, tag, ledger):
    from src import llm
    r = llm.chat(model, [{"role": "system", "content": system}, {"role": "user", "content": user}], temperature=temperature, max_tokens=500, tag=tag)
    ledger.append(r["cost_usd"] if not r["cached"] else 0.0)
    try:
        return json.loads(r["text"])
    except Exception:
        return {}


def norm(x): return re.sub(r"[^a-z0-9]+", " ", str(x).lower()).strip()
def toks(x): return {t for t in norm(x).split() if len(t) > 2}


def compare(hid, ext, note=""):
    """Return a list of mismatches between hidden facts and the blind extraction (name-like facts are checked against the note text itself)."""
    bad = []; nn = norm(note)
    for k, v in hid.items():
        if k in ("approval_ref", "city"):
            continue
        e = ext.get(k)
        if k == "expense_type":
            if v != "OTHER" and e != v:
                bad.append(f"expense kind read as {e}, should be {v}")
            continue
        if k == "charge_to":
            if v == "PROJECT" and e != "PROJECT":
                bad.append("the note must say the cost goes to a project budget and quote the project id")
            continue
        if k in ("origin_type", "destination_type") and v not in ("HOME", "OFFICE"):
            continue
        if v in (None, ""):
            if e not in (None, "", 0):
                bad.append(f"{k} must not be recoverable from the note but was read as {e!r}")
            continue
        if k in ("alcohol_amount", "tip_amount", "external_attendees") and not v:
            if e not in (None, 0, 0.0, ""):
                bad.append(f"{k} should be zero/none but was read as {e!r}")
            continue
        if isinstance(v, (int, float)):
            try:
                if abs(float(e) - float(v)) > 0.01 * max(1, abs(float(v))):
                    bad.append(f"{k} should be {v} but was read as {e!r}")
            except Exception:
                bad.append(f"{k} should be {v} but could not be read ({e!r})")
        elif k in ("conference_ref", "exception_ref", "learning_plan_id"):
            if re.sub(r"[^a-z0-9]", "", str(e).lower()) != re.sub(r"[^a-z0-9]", "", str(v).lower()):
                bad.append(f"{k} should be {v} but was read as {e!r}")
        elif k in ("external_names", "recipient_name", "business_owner", "origin", "destination", "item", "provider", "recipient_org"):
            need = toks(v) or {norm(v)}
            if not any(t and t in nn for t in need):
                bad.append(f"the note must contain {v!r} ({k})")
            elif k == "recipient_org" and norm(v) not in nn:
                bad.append(f"recipient_org must appear exactly as {v!r}")
        else:
            if norm(v) != norm(e):
                bad.append(f"{k} should be {v} but was read as {e!r}")
    return bad


def visible_claim(c, note):
    b = dict(c["bill"]); b["line_items"] = [dict(description="Charges", amount=b["total"])]; b["merchant_category"] = COARSE.get(b["merchant_category"], "OTHER")
    return dict(case_id=c["case_id"], employee_id=c["employee_id"], transaction_date=c["transaction_date"], submission_date=c["submission_date"], bill=b, form={}, employee_description=note, project_id=c["project_id"], split=c.get("split"))


def process(c, S, rng, cached):
    """Draft -> validate (blind extraction, engine re-run, leak/length) with up to 3 attempts."""
    style = c["_style"]; flavor = c["_flavor"]; ledger = []; fb = ""; last = None
    hid = c["_hidden_form"]
    for attempt in range(4):
        if cached and attempt == 0 and c["_key"] in cached:
            note = cached[c["_key"]]["note"]
        else:
            s = style if attempt < (3 if style == "local" else 2) else ("challenge" if style == "challenge" else "indirect")
            d = call(MODEL, SYSTEM_DRAFT, draft_prompt(c, s, flavor, fb, explicit=attempt >= 2), 0.7 if attempt == 0 else 0.5, "SEM_DRAFT", ledger)
            note = (d.get("note") or "").strip()
        problems = []
        wc = max(len(note.split()), len(note) // (3 if re.search(r"[\u3000-\u9fff]", note) else 5))   # unspaced CJK text: characters/3
        if not (12 <= wc <= 110): problems.append(f"length {wc} words is outside 12-110")
        m = FORBID.search(note)
        if m: problems.append(f"contains forbidden wording {m.group(0)!r}")
        if not problems:
            ext = call(MODEL, SYSTEM_EXTRACT, f"Bill: merchant {c['bill']['merchant']} ({c['bill']['city']}, {c['bill']['country']}), total {c['bill']['total']} {c['bill']['currency']}, transaction date {c['transaction_date']}.\nEmployee note: {note}", 0.0, "SEM_EXTRACT", ledger)
            problems += compare(hid, ext, note) if c["_arch"] != "A9" else []
            probe = dict(c, form=hid, employee_description=note)
            try:
                if engine.evaluate(probe, S)["expected_decision"] != c["_gt"]["expected_decision"]:
                    problems.append("the engine's keyword conflict check changes the outcome: avoid words naming a different kind of expense than the bill (taxi, hotel, dinner, flight) unless they match it")
            except Exception as e:  # noqa
                problems.append("engine error " + repr(e)[:60])
        last = dict(note=note, style=style if attempt < 2 else "indirect", attempts=attempt + 1, problems=problems, cost=sum(ledger))
        if not problems:
            return last
        fb = "; ".join(problems)[:500]
    if c["_arch"] == "A9" and last and last["problems"]:   # evidence-conflict claims depend on keyword mismatch: fall back to the original (already validated) short note
        note = c["_orig_desc"]; last = dict(note=note, style="original", attempts=last["attempts"], problems=[], cost=last["cost"], manual_review="Evidence-conflict claim: the LLM rewrite kept failing the conflict check, so the original short note is used.")
    return last


def apply(cases, S, workers=6):
    rng = random.Random(W.SEED + 31)
    cached = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    order = sorted(cases, key=lambda c: c["_key"])
    for c in order:
        c["_hidden_form"] = c["form"]; c["_orig_desc"] = c["employee_description"]; c["_hidden_cat"] = c["bill"]["merchant_category"]
        reg = W.COUNTRY_TO_REGION[c["bill"]["country"]]
        pool = ["indirect"] * 4 + ["terse"] * 3 + ["verbose"] * 4 + ["secondhand"] * 3 + ["dictated"] * 3 + {"JP": ["local"] * 7, "IN": ["local"] * 4 + ["mixed"] * 2, "SG": ["indirect"] * 3}[reg]
        c["_style"] = "challenge" if c.get("_challenge") else rng.choice(pool); c["_flavor"] = flavor_for(c, rng); c["_derive"] = derive_for(c, rng); c["_noise"] = noise_for(c, rng)
    total = 0.0; results = {}
    with ThreadPoolExecutor(workers) as ex:
        futs = {c["_key"]: ex.submit(process, c, S, rng, cached) for c in order}
        for k, fu in futs.items():
            r = fu.result(); results[k] = r; total += r["cost"]
    for k, why in MANUAL_OK.items():   # (problem substring, reason)
        r = results.get(k)
        if r and r["problems"] and all(why[0] in p for p in r["problems"]):
            r["problems"] = []; r["manual_review"] = why[1]
    if total > BUDGET_USD: raise RuntimeError(f"semantic layer cost {total:.3f} above cap")
    out = {}
    for c in cases:
        r = results[c["_key"]]; c["_sem"] = r; c["_vis"] = visible_claim(c, r["note"])
        out[c["_key"]] = dict(note=r["note"], style=r["style"], attempts=r["attempts"], problems=r["problems"], manual_review=r.get("manual_review"))
    CACHE.write_text(json.dumps(out, indent=1))
    failed = [k for k, r in results.items() if r["problems"]]
    return dict(cost_usd=round(total, 4), n=len(cases), validated=len(cases) - len(failed), failed=failed, attempts={a: sum(r["attempts"] == a for r in results.values()) for a in (1, 2, 3, 4)})
