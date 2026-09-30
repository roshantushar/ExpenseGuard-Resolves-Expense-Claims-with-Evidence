"""ExpenseGuard V2 - normative policy text. Every number is rendered from world.py, the same source the reference engine reads."""
from __future__ import annotations
from . import world as W

CO = "Northstar Analytics Group"


def m(v, ccy="SGD"):
    return f"{ccy} {v:,.2f}" if isinstance(v, float) and v != int(v) else f"{ccy} {int(v):,}"


def tbl(headers, rows):
    return "\n".join(["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)] + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows])


def C(id_, title, text): return dict(id=id_, title=title, text=text.strip())


def circ_text(a):
    if a.get("note"):
        return a["note"]
    if a["kind"] == "pct":
        return (f"With effect from {a['eff']}, the {a['sched'].lower().replace('_', ' ')} amounts for {a['key']} in the schedule for {a['eff'][:4]} are increased by {a['value']} percent, "
                f"rounded half up to the nearest {a['round']}. The increase applies to every grade band and to transactions dated on or after the effective date and within {a['eff'][:4]}.")
    return (f"With effect from {a['eff']}, the amount in the schedule for {a['key'] if a['key'] != 'ALL' else 'all rows'} is replaced by {a['value']:g} for transactions dated on or after the effective date "
            f"and within {a['eff'][:4]}. Earlier transactions remain governed by the value published for their date.")


def docs():
    D = []
    # ------------------------------------------------ D01-D03 global policies
    for yy, y in ((24, 2024), (25, 2025), (26, 2026)):
        s = W.SUBMIT[y]
        late = (f"Claims must be submitted within {s['ok']} calendar days of the transaction date. A claim submitted later is rejected unless an approved exception exists." if y == 2024 else
                f"Claims must be submitted within {s['ok']} calendar days of the transaction date. A claim submitted from day {s['ok'] + 1} up to and including day {s['approval']} requires manager approval. "
                f"A claim submitted after day {s['approval']} is escalated to Finance." )
        cl = [
            C(f"GEP{yy}-1.1", "Purpose and scope", f"This policy governs reimbursement of business expenses incurred by employees of {CO} and its subsidiaries for transactions dated between 1 January {y} and 31 December {y}. "
              f"Transactions dated in another calendar year are governed by the policy version published for that year."),
            C(f"GEP{yy}-1.2", "Business purpose", {2024: "Every expense must have a clear business purpose connected to company activity. Personal benefit alone is not reimbursable.",
              2025: "Expenses must primarily support company business. Mixed personal and business expenses require itemisation and only the documented business portion may be considered.",
              2026: "Every expense must have a specific, auditable business purpose. Generic wording such as business expense or client activity is insufficient where a category policy requires named attendees, a route, an event, or a project."}[y]),
            C(f"GEP{yy}-1.3", "Documentation", "A claim must state the merchant, transaction date, currency, total amount and a description sufficient to determine the business purpose. Category policies may require additional fields; where a required field is absent the claim cannot be approved."),
            C(f"GEP{yy}-2.1", "Submission window", late),
            C(f"GEP{yy}-2.2", "Late submission and outage relief", "Late submission tiers are counted in calendar days from the transaction date to the submission date. Formally recorded Finance system outage relief is published by circular and applies only to transactions dated inside the stated outage window."),
            C(f"GEP{yy}-2.3", "Currency", "Thresholds expressed in SGD equivalent are tested as set out in the Currency and FX Handling Policy. Ceilings expressed in a local currency are tested in that currency without conversion."),
            C(f"GEP{yy}-3.1", "Order of precedence", "Where rules differ, the order of precedence is: law and regulation; the applicable regional addendum; a Finance circular from its effective date, which amends the clause it names; an approved written exception within its stated scope; the category policy; this global policy; and finally definitions, frequently asked questions and worked examples, which never override the clauses above."),
            C(f"GEP{yy}-3.2", "Circulars", "A Finance circular amends the clause it names from its effective date only. A transaction dated before the effective date is decided under the value that applied on its own transaction date."),
            C(f"GEP{yy}-4.1", "Insufficient evidence", "If a mandatory fact cannot be determined from the claim or from approved enterprise records, the reviewer requests the missing information from the employee. Facts must not be inferred from the employee narrative when an authoritative record exists."),
            C(f"GEP{yy}-4.2", "Human review", "A claim is escalated to Finance where two rules conflict and precedence cannot be determined from published text, where an approval conflicts with the transaction facts, or where the amount exceeds the Finance review threshold in the Approval Authority Policy."),
            C(f"GEP{yy}-5.1", "Applicability by date", f"This policy version applies only to transactions dated in {y}. A later version does not apply retrospectively and an earlier version does not apply to a later transaction."),
            C(f"GEP{yy}-5.2", "Mixed expenses", "A bill that combines personal and business items must be itemised. If the business amount cannot be separated from the personal amount, the claim is returned for the business amount rather than approved in full."),
        ]
        if y >= 2025:
            cl.append(C(f"GEP{yy}-6.1", "Evidence standard", "A decision must cite the applicable clause and every enterprise fact that the clause requires. The travel request is the authoritative source for trip approval and destination; employee narrative never overrides a system record."))
        if y == 2026:
            cl.append(C(f"GEP{yy}-6.2", "Automation boundary", "Automated systems may recommend a disposition but must not create payments or modify live financial records. All automated recommendations are logged with the evidence relied on."))
        D.append(dict(id=f"D{yy - 23:02d}", key=f"GEP{yy}", title=f"Global Expense Policy {y}", region="GLOBAL", eff=(f"{y}-01-01", f"{y}-12-31"), category="general", rank=6, clauses=cl))

    # ------------------------------------------------ D04 travel and accommodation
    hot = []
    for y, cid in ((2024, "TRV-3.1"), (2025, "TRV-3.2"), (2026, "TRV-3.3")):
        rows = []
        for loc in W._H:
            ccy = "SGD" if loc.startswith("SG") else "INR" if loc.startswith("IN") else "JPY"
            rows.append([loc, ccy] + [f"{W.HOTEL.base[(loc, b)][y]:,}" for b, _, _ in W.BANDS])
        hot.append(C(cid, f"Nightly hotel ceilings {y}", f"The nightly base ceilings for transactions dated in {y} are set out below in local currency. The ceiling is compared with the nightly rate, which is the total accommodation charge divided by the number of nights.\n\n"
                     + tbl(["Location tier", "Currency"] + [b for b, _, _ in W.BANDS], rows) + "\n\nCircular amendments to a row apply from their effective date as set out in the Finance Circulars."))
    D.append(dict(id="D04", key="TRV", title="Travel and Accommodation Policy", region="GLOBAL", eff=("2024-01-01", "2099-12-31"), category="travel", rank=5, clauses=[
        C("TRV-1.1", "Trip authorisation", "Hotel and airfare expenses require an approved business trip covering the transaction date, evidenced by the travel request record, unless a valid written exception removes the requirement. A request that is pending, rejected or absent does not evidence approval."),
        C("TRV-1.2", "Travel request statuses", "A travel request has one of the statuses APPROVED, PENDING or REJECTED. Only APPROVED evidences an authorised trip. A request may reference a conference event identifier and an exception identifier, which are then looked up in their own records."),
        C("TRV-2.1", "Hotel principles", "Hotel accommodation is reimbursable for single occupancy during an approved business trip up to the nightly ceiling for the destination tier and the employee grade band. The employee grade is taken from the employee profile record."),
        C("TRV-2.2", "Location tiers", "Destinations are classified into ceiling tiers as follows.\n\n" + tbl(["City", "Ceiling tier"], [[c, loc] for c, loc in W.CITY_LOC.items()]) + "\n\nA city not listed takes the lowest tier for its country."),
        *hot,
        C("TRV-3.4", "Applying amendments", "A percentage amendment to a hotel row is applied to the base ceiling for the transaction year, rounded half up to the rounding unit stated in the circular. An amendment does not compound with another amendment on the same row in the same year."),
        C("TRV-4.1", "Long stays", f"For a stay of more than {W.LONG_STAY_NIGHTS} nights, from 1 January 2025, the ceiling applied to the nightly rate is {W.LONG_STAY_FACTOR} percent of the ceiling that would otherwise apply."),
        C("TRV-4.2", "Nightly rate", "The nightly rate is the total accommodation charge on the bill divided by the number of nights stated on the claim. Incidentals billed separately are claimed under their own categories."),
        C("TRV-5.1", "Conference lodging", "Where the travel request references an approved conference, the Training and Conferences Policy is consulted before a hotel is rejected solely for exceeding the ordinary ceiling."),
        C("TRV-5.2", "Partner hotel uplift", f"For a registered attendee of an approved conference staying at the official partner hotel named in the conference registry, the nightly ceiling is increased by {W.CONF_UPLIFT[2024]} percent in 2024, {W.CONF_UPLIFT[2025]} percent in 2025 and {W.CONF_UPLIFT[2026]} percent in 2026. The uplift applies after any percentage amendment and before the long-stay factor."),
        C("TRV-6.1", "Ceiling exceptions", "A nightly rate above the applicable ceiling is reimbursable only through the partner hotel uplift or an approved hotel-limit exception under the Exceptions and Waivers Procedure."),
        C("TRV-6.2", "Evidence hierarchy", "The travel request is the authoritative source for trip approval, destination and linked identifiers. The description written by the employee cannot substitute for a missing record."),
        C("TRV-7.1", "Personal extension", "Cost attributable to a personal extension of a business trip is not reimbursable. Where the comparison with the business-only stay is missing, the reviewer requests it."),
    ]))
    # ------------------------------------------------ D05 air and rail
    D.append(dict(id="D05", key="AIR", title="Air and Rail Travel Standards", region="GLOBAL", eff=("2024-01-01", "2099-12-31"), category="travel", rank=5, clauses=[
        C("AIR-1.1", "Standard cabin", "Economy class is the standard cabin for all flights. Fares are booked through the corporate travel tool or a comparable fare is documented."),
        C("AIR-2.1", "Premium economy", f"Premium economy is permitted where the scheduled flight time exceeds {W.AIR_PE_HOURS.base['ALL'][2024]:g} hours and the traveller is grade G{W.AIR['pe_min_grade']} or above. The hours threshold is published in the schedule and may be amended by circular."),
        C("AIR-2.2", "Business class", f"Business class is permitted for grade G{W.AIR['biz_min_grade']} and above, or for grade G{W.AIR['biz_hours_grade']} and above where the scheduled flight time exceeds {W.AIR['biz_hours']:g} hours. Otherwise business class requires an approved travel exception naming the flight."),
        C("AIR-3.1", "Advance booking", f"A fare booked fewer than {W.AIR['advance_days']} days before departure requires manager approval. The days are counted from booking date to departure date."),
        C("AIR-3.2", "Changes and cancellations", "Change and cancellation fees are reimbursable only where the change was required by the business and is evidenced by the travel record."),
        C("AIR-4.1", "Rail", "Rail travel follows the regional addendum. Where the addendum is silent, the standard class of service applies and a higher class requires approval."),
    ]))
    # ------------------------------------------------ D06 ground transport
    D.append(dict(id="D06", key="GRD", title="Ground Transportation Policy", region="GLOBAL", eff=("2024-01-01", "2099-12-31"), category="transport", rank=5, clauses=[
        C("GRD-1.1", "Business ground transport", "Taxi and ride-hailing are reimbursable for travel between business locations, an airport, a hotel, a client site or an approved event. The claim must state the origin and the destination."),
        C("GRD-1.2", "Commuting", "Ordinary travel between home and the usual place of work is a commute and is not reimbursable, except under the late-night rule."),
        C("GRD-2.1", "Late-night travel", f"Home transport departing after {W.LATE_NIGHT['start']} is reimbursable where documented business activity ended after {W.LATE_NIGHT['activity_end']}. The claim must state the route and the activity that ended late."),
        C("GRD-3.1", "Car rental", f"Car rental requires manager approval and is available to grade G{W.CARD_RENTAL_MIN_GRADE} and above."),
        C("GRD-4.1", "Private vehicle mileage", "Use of a private vehicle is reimbursed at the per-kilometre rate published in the regional addendum multiplied by the distance stated on the claim. A claim for more than the calculated amount cannot be approved as submitted."),
        C("GRD-5.1", "Parking and tolls", "Parking and tolls are reimbursable when incurred on business travel and evidenced by a receipt naming the location."),
    ]))
    # ------------------------------------------------ D07 meals
    D.append(dict(id="D07", key="MEAL", title="Meals and Entertainment Policy", region="GLOBAL", eff=("2024-01-01", "2099-12-31"), category="meals", rank=5, clauses=[
        C("MEAL-1.1", "Employee meals", "A meal consumed only by employees during ordinary work is reimbursable up to the per-person employee meal ceiling in the regional addendum and requires a business reason beyond routine attendance. The ceiling is applied to the total divided by the number of attendees."),
        C("MEAL-1.2", "Client meals", "A meal with at least one external attendee is a client meal. The claim must name the external attendees or their organisations and the business purpose. Per-attendee spend is the total divided by all attendees present, including employees, and is compared with the regional client meal ceiling."),
        C("MEAL-1.3", "Business entertainment", "External entertainment that is primarily recreational is tested against the per-external-attendee entertainment ceiling in the regional addendum, not the client meal ceiling, and requires manager approval above the approval threshold for entertainment."),
        C("MEAL-1.4", "Attendee status", "An attendee is an employee only if they are on the payroll of the company or of one of its subsidiaries, including interns and secondees on payroll. Freelance consultants, agency staff, contractors and staff of partner or customer firms are external attendees even when they work alongside employees every day. The role a person plays in the meeting does not change their status."),
        C("MEAL-2.1", "Alcohol", "Alcohol follows the regional addendum. Where permitted, it must be incidental to an otherwise reimbursable client meal or event and its share of the bill is limited as the addendum states."),
        C("MEAL-2.2", "Tips and service charges", f"Mandatory service charges are reimbursable. A voluntary gratuity above {W.TIP_MAX_PCT} percent of the pre-tip bill requires manager approval unless the regional addendum is stricter."),
        C("MEAL-3.1", "Default ceilings for locations without an addendum", f"For a country with no regional addendum the employee meal ceiling is {m(60)} per person and the client meal ceiling is {m(110)} per attendee. These defaults never apply to Singapore, India or Japan."),
        C("MEAL-3.2", "Attendee evidence", "If the attendee count is needed for a per-person test and cannot be established from the claim, the reviewer requests it."),
        C("MEAL-4.1", "Mixed-purpose events", "Where an event combines employee-only and external activity and the allocation is unclear, the reviewer requests clarification instead of choosing the more generous ceiling."),
        C("MEAL-5.1", "Meals during conferences", "Meals included in a conference fee cannot also be claimed separately. Where inclusion is unclear the reviewer requests the conference programme."),
    ]))
    # ------------------------------------------------ D08 gifts
    D.append(dict(id="D08", key="GIFT", title="Client Gifts and Hospitality Policy", region="GLOBAL", eff=("2024-01-01", "2099-12-31"), category="gifts", rank=5, clauses=[
        C("GIFT-1.1", "Purpose", "Modest gifts to external business contacts are reimbursable where they support an existing business relationship and are neither lavish nor intended to influence a decision improperly."),
        C("GIFT-1.2", "Prohibited recipients", "A gift to a public official, a government-affiliated body or a person who is a decision-maker in an open tender involving the company is prohibited and is rejected regardless of value."),
        C("GIFT-1.3", "Cash and equivalents", "Cash, gift cards, vouchers and other cash equivalents are prohibited as gifts and are rejected."),
        C("GIFT-1.5", "Government-affiliated bodies", "A government-affiliated body is a ministry, department, agency, statutory board or authority, a municipal or regional body, a public university or hospital, and any company that is owned or controlled by the state. A recipient does not stop being government-affiliated because it trades commercially or has a corporate-sounding name."),
        C("GIFT-1.6", "What counts as a cash equivalent", "A cash equivalent is any stored-value or exchangeable instrument: gift cards, prepaid or reloadable cards, e-vouchers, redeemable codes, store credit and any item that the recipient can exchange for money. The instrument is a cash equivalent whether it is delivered on paper, by message or by e-mail."),
        C("GIFT-1.4", "Required details", "A gift claim must state the recipient name, the recipient organisation and the business purpose. A claim missing any of them is returned for the missing details."),
        C("GIFT-2.1", "Per-gift ceiling", "The value of a single gift to one recipient may not exceed the per-gift ceiling in the regional addendum for the transaction date."),
        C("GIFT-2.2", "Annual ceiling", "The total of gifts to the same recipient organisation in a calendar year, including the current claim, may not exceed the annual ceiling in the regional addendum. Earlier gifts are found in the previous expense records."),
        C("GIFT-3.1", "Hospitality distinguished", "A shared meal is governed by the Meals and Entertainment Policy. A gift is an item given to a recipient to keep."),
    ]))
    # ------------------------------------------------ D09 card and personal
    D.append(dict(id="D09", key="CARD", title="Corporate Card and Personal Spend Policy", region="GLOBAL", eff=("2024-01-01", "2099-12-31"), category="card", rank=5, clauses=[
        C("CARD-1.1", "Personal spend", "Purely personal purchases are not reimbursable even when paid with a corporate card."),
        C("CARD-1.2", "Accidental personal use", "An accidental personal purchase on a corporate card is rejected for reimbursement and handled by the repayment process outside expense review."),
        C("CARD-2.1", "Consumer services", "Streaming, gaming, personal fitness, household utilities and other consumer services are presumed personal unless a category policy names the specific business use."),
        C("CARD-3.1", "Merchant risk classes", "Each merchant in the merchant directory carries a risk class. STANDARD merchants are ordinary. RESTRICTED_PROHIBITED merchants, such as casinos and adult entertainment venues, are not reimbursable and the claim is rejected. RESTRICTED_REVIEW merchants, such as prepaid-card resellers, require Finance review and the claim is escalated."),
        C("CARD-4.1", "Merchant lookup", "The merchant risk class is taken from the merchant directory, not from the merchant name as typed on the claim."),
    ]))
    # ------------------------------------------------ D10 approval authority
    am, ad, af = W.APPROVAL_SGD["manager"], W.APPROVAL_SGD["director"], W.APPROVAL_SGD["finance"]
    D.append(dict(id="D10", key="APR", title="Approval Authority, Delegation and Budget Control Policy", region="GLOBAL", eff=("2024-01-01", "2099-12-31"), category="approval", rank=5, clauses=[
        C("APR-1.1", "Manager approval", f"A single discretionary expense above {m(am[2024])} equivalent requires manager approval. The regional addenda may set a lower local threshold, which then controls."),
        C("APR-1.2", "Director approval", f"A single discretionary expense above {m(ad[2024])} equivalent requires director approval for transactions dated in 2024 and 2025, and above {m(ad[2026])} equivalent for transactions dated in 2026."),
        C("APR-1.3", "Finance review", f"A single discretionary expense above {m(af[2024])} equivalent requires Finance review and is escalated. An exception to a prohibited category or a conflict between an approval and the transaction facts also requires Finance review."),
        C("APR-2.1", "Approval validity", "An approval is valid only if its status is APPROVED, it names the employee, its type covers the expense category, it covers the transaction date, and the approver level is at least the level the amount requires. Approval types are GENERAL, TRAVEL, SOFTWARE, ENTERTAINMENT, TRAINING and COMBINED_SPEND."),
        C("APR-2.2", "Approval scope", "An approval cannot be reused for another employee, another category or another date range unless it says so. An approval whose type does not cover the expense is treated as conflicting evidence."),
        C("APR-3.1", "Missing approval", "Where an approval is required and no valid approval record exists, the reviewer requests it from the employee. Where the amount requires Finance review, or the approval evidence conflicts, the claim is escalated instead."),
        C("APR-4.1", "Delegation", "A manager who is unavailable may delegate approval authority. The approval record then has the status DELEGATED and references a delegation record. The delegation is valid only on dates inside its validity period and only for amounts up to its stated SGD limit, and the delegate must hold the approver level the amount requires."),
        C("APR-4.2", "Invalid delegation", "If the delegation is outside its validity period, the reviewer requests a valid approval. If the delegation is valid but the amount exceeds its limit or the delegate holds a lower level than the amount requires, the claim is escalated."),
        C("APR-5.1", "Cost-centre budget", f"Where a claim is charged to a cost centre whose status is FROZEN, any expense above {m(W.CC_FROZEN_MIN_SGD)} equivalent is escalated to Finance. Where the remaining budget of an OPEN cost centre is smaller than the claim amount, the reviewer requests budget-owner approval."),
        C("APR-5.2", "Project hierarchy", "A project that has a parent project is charged to the cost centre of the parent project. The parent project, if any, is looked up in the project registry."),
    ]))
    # ------------------------------------------------ D11 exceptions
    D.append(dict(id="D11", key="EXC", title="Exceptions and Waivers Procedure", region="GLOBAL", eff=("2024-01-01", "2099-12-31"), category="exceptions", rank=4, clauses=[
        C("EXC-1.1", "What an exception is", "An exception is a written waiver approved in advance that permits a stated departure from a stated policy for a stated employee and date range. It is recorded in the exception register with an identifier."),
        C("EXC-1.2", "Scope", "An exception is valid only if its status is APPROVED, it names the employee, its policy identifier is the policy being departed from, and the transaction date lies inside its validity dates."),
        C("EXC-2.1", "Outcomes", "If a cited exception is valid, the departure it permits is accepted. If it is not APPROVED or the transaction date lies outside its validity dates, the departure is not permitted and the claim is decided under the ordinary rule. If it names a different policy or employee, the claim is escalated to Finance. If the cited identifier does not exist, the reviewer requests the correct reference."),
        C("EXC-2.2", "Where the identifier comes from", "The exception identifier may be quoted on the claim, or may be linked from the travel request record. A linked identifier is looked up in the exception register."),
        C("EXC-3.1", "No exception for prohibitions", "No exception can permit a prohibited category, a prohibited recipient or a prohibited merchant class."),
    ]))
    # ------------------------------------------------ D12 training
    tr = []
    for y, cid in ((2024, "TRN-2.1"), (2025, "TRN-2.2"), (2026, "TRN-2.3")):
        tr.append(C(cid, f"Annual external training ceilings {y}", f"The calendar-year ceiling for external training spend per employee, in SGD equivalent, for transactions dated in {y}:\n\n"
                    + tbl(["Grade band", "Annual ceiling (SGD)"], [[b, f"{W.TRAIN_CAP.base[b][y]:,}"] for b, _, _ in W.BANDS]) + "\n\nSpend already reimbursed in the same calendar year counts towards the ceiling."))
    D.append(dict(id="D12", key="TRN", title="Training, Certification and Conferences Policy", region="GLOBAL", eff=("2024-01-01", "2099-12-31"), category="training", rank=5, clauses=[
        C("TRN-1.1", "Conference registration", "Conference fees are reimbursable only for approved professional events relevant to the employee role, evidenced by a REGISTERED entry in the conference registry."),
        C("TRN-1.2", "Event evidence", "The conference registry or the approved travel record establishes event approval. The employee description alone is insufficient where an exception or uplift depends on event status."),
        *tr,
        C("TRN-2.4", "Learning plan", "A training claim must quote the learning plan identifier. A claim without it is returned for the identifier."),
        C("TRN-2.5", "Exceeding the ceiling", "Cumulative training spend above the annual ceiling requires director approval of type TRAINING. Without a valid approval the reviewer requests it."),
        C("TRN-3.1", "Certification exams", "Professional certification exam fees require manager approval and an active role-development plan, quoted on the claim."),
        C("TRN-4.1", "Official partner hotel", "A hotel is an official partner hotel only if it is the partner named in the conference registry entry for the employee."),
    ]))
    # ------------------------------------------------ D13 software and equipment
    D.append(dict(id="D13", key="SWE", title="Software, Subscriptions and Equipment Policy", region="GLOBAL", eff=("2024-01-01", "2099-12-31"), category="software", rank=5, clauses=[
        C("SWE-1.1", "Subscriptions", f"A software or online service subscription requires a named business owner on the claim. Up to {m(W.SOFTWARE_TIERS['low'])} equivalent no approval is required. Above it, manager approval of type SOFTWARE or GENERAL is required."),
        C("SWE-1.2", "Larger subscriptions", f"From 1 February 2026 a subscription above {m(W.SOFTWARE_TIERS['high'])} equivalent requires manager approval, an ACTIVE project record and an OPEN cost centre. If the project is not active or the cost centre is not open, the claim is escalated."),
        C("SWE-1.3", "Prepaid annual plans", f"A prepaid annual plan above {m(W.SOFTWARE_TIERS['prepaid_finance'])} equivalent must be procured through Finance and the claim is escalated."),
        C("SWE-2.1", "Equipment", f"Equipment up to {m(W.EQUIP['no_approval'])} equivalent is reimbursable. Equipment above that and up to {m(W.EQUIP['approval'])} equivalent requires manager approval. Equipment above {m(W.EQUIP['approval'])} equivalent is a capital asset and must be procured through Finance; the reimbursement claim is rejected."),
        C("SWE-2.2", "Personal devices", "Devices primarily for personal use are not reimbursable."),
    ]))
    # ------------------------------------------------ D14 telecom
    D.append(dict(id="D14", key="TEL", title="Telecommunications Policy", region="GLOBAL", eff=("2024-01-01", "2099-12-31"), category="telecom", rank=5, clauses=[
        C("TEL-1.1", "Business mobile and data", "Business use of a personal mobile plan is reimbursable up to the monthly ceiling in the regional addendum."),
        C("TEL-1.2", "Cumulative monthly claims", "The monthly ceiling applies to the sum of all telecommunications claims by the employee in the calendar month of the transaction, including the current claim. Earlier claims are found in the previous expense records."),
        C("TEL-2.1", "Excess", "A claim that would take the monthly total above the ceiling cannot be approved as submitted."),
    ]))
    # ------------------------------------------------ D15 duplicates
    D.append(dict(id="D15", key="DUP", title="Duplicate, Split and Recurring Expense Controls", region="GLOBAL", eff=("2024-01-01", "2099-12-31"), category="controls", rank=5, clauses=[
        C("DUP-1.1", "Exact duplicate", "A claim with the same employee, the same merchant and the same bill number as a reimbursed expense, or the same employee, merchant, transaction date and amount, is an exact duplicate and is rejected."),
        C("DUP-1.2", "Near duplicate", f"A claim by the same employee at the same merchant within {W.NEAR_DUP_DAYS} days of an earlier expense, with an amount within {W.NEAR_DUP_TOL_PCT} percent of it and a different bill number, is a possible duplicate. The reviewer requests clarification from the employee."),
        C("DUP-1.3", "Recurring charges", f"A recurring charge is a repeat at the same merchant by the same employee between {W.RECUR_MIN} and {W.RECUR_MAX} days after an earlier expense whose purpose is recurring, with an amount within 5 percent. It is not a duplicate."),
        C("DUP-2.1", "Split transactions", f"Purchases by the same employee at the same merchant for the same project within {W.SPLIT_DAYS} days of each other, whose amounts differ by more than {W.NEAR_DUP_TOL_PCT} percent, are treated together. The combined amount governs the approval threshold."),
        C("DUP-2.2", "Approval for combined spend", "Where the combined amount crosses an approval threshold that each purchase alone did not, an approval of type COMBINED_SPEND is required. If none exists the reviewer requests it. If an approval exists but of another type, the evidence conflicts and the claim is escalated."),
    ]))
    # ------------------------------------------------ D16 FX
    D.append(dict(id="D16", key="FX", title="Currency and FX Handling Policy", region="GLOBAL", eff=("2024-01-01", "2099-12-31"), category="fx", rank=5, clauses=[
        C("FX-1.1", "SGD equivalent", "An amount in another currency is converted to SGD using the monthly rate in the FX rate table for the calendar month of the transaction date. The converted amount is not rounded before it is compared with a threshold."),
        C("FX-1.2", "Which tests use SGD", "Approval thresholds expressed in SGD equivalent, software tiers and equipment tiers are tested on the SGD equivalent. Regional ceilings and regional approval thresholds expressed in a local currency are tested in that currency."),
        C("FX-1.3", "Comparison", "A threshold is crossed when the amount is strictly greater than the threshold. An amount equal to the threshold does not cross it."),
        C("FX-1.4", "Card-posted amounts", "The amount posted on a corporate card statement is not used for threshold tests."),
    ]))
    # ------------------------------------------------ D17-D19 regional addenda
    for did, R, name in (("D17", "SG", "Singapore"), ("D18", "IN", "India"), ("D19", "JP", "Japan")):
        ccy = W.REGION[R]["ccy"]
        def rowsfor(S): return [[y, f"{S.base[R][y]:,}"] for y in W.YEARS]
        cl = [
            C(f"{R}-1.1", "Scope and precedence", f"This addendum applies to transactions incurred in {name}. Where it differs from a global policy for the same subject, this addendum controls, and a Finance circular that names one of its clauses amends that clause from the effective date."),
            C(f"{R}-2.1", "Employee meal ceiling", f"The employee-only meal ceiling per person, in {ccy}, is:\n\n" + tbl(["Year", f"Ceiling ({ccy})"], rowsfor(W.EMP_MEAL))),
            C(f"{R}-2.2", "Client meal ceiling", f"The client meal ceiling per attendee, including employees present, in {ccy}, is:\n\n" + tbl(["Year", f"Ceiling ({ccy})"], rowsfor(W.CLIENT_MEAL))),
            C(f"{R}-2.3", "Entertainment ceiling", f"The entertainment ceiling per external attendee, in {ccy}, is:\n\n" + tbl(["Year", f"Ceiling ({ccy})"], rowsfor(W.ENTERTAIN))),
            C(f"{R}-3.1", "Gift ceiling per gift", f"The ceiling for a single gift to one recipient, in {ccy}, is:\n\n" + tbl(["Year", f"Ceiling ({ccy})"], rowsfor(W.GIFT))),
            C(f"{R}-3.2", "Annual gift ceiling per recipient organisation", f"The calendar-year ceiling for gifts to one recipient organisation, in {ccy}, is:\n\n" + tbl(["Year", f"Ceiling ({ccy})"], rowsfor(W.GIFT_ANNUAL))),
            C(f"{R}-4.1", "Mileage rate", f"The private vehicle mileage rate per kilometre, in {ccy}, is:\n\n" + tbl(["Year", f"Rate ({ccy} per km)"], [[y, f"{W.MILEAGE.base[R][y]:g}"] for y in W.YEARS])),
            C(f"{R}-5.1", "Telecom monthly ceiling", f"The monthly telecommunications ceiling per employee, in {ccy}, is:\n\n" + tbl(["Year", f"Ceiling ({ccy})"], rowsfor(W.TELECOM))),
        ]
        if R == "SG":
            cl += [C("SG-2.4", "Alcohol", f"Alcohol is permitted only with external attendees and may not exceed {W.ALCOHOL['SG'][2024]} percent of the total bill in 2024 and 2025, and {W.ALCOHOL['SG'][2026]} percent in 2026."),
                   C("SG-2.5", "Tips", "Service charges are ordinarily included. A voluntary gratuity above the global limit requires manager approval."),
                   C("SG-4.2", "Taxi", "Taxi and ride-hailing within Singapore follow the Ground Transportation Policy."),
                   C("SG-6.1", "Approval thresholds", "The global approval thresholds in SGD equivalent apply without change."),
                   C("SG-6.2", "Entertainment approval", f"Entertainment requires manager approval where the total exceeds {m(W.SOFTWARE_TIERS['low'])}.")]
        if R == "IN":
            cl += [C("IN-2.4", "Alcohol prohibition", "Alcohol is not reimbursable for transactions in India, including client entertainment, regardless of any approval."),
                   C("IN-2.5", "Tips", f"Voluntary gratuity above {W.TIP_MAX_PCT} percent of the bill requires manager approval."),
                   C("IN-4.2", "Local transport", "App-based taxi is reimbursable for approved business travel; the normal commute is not. Rail follows the class entitlement for the grade."),
                   C("IN-6.1", "Approval thresholds", f"Manager approval is required for any single discretionary expense above {m(W.REGIONAL_MGR['IN'][2024], 'INR')} in local currency, which is stricter than the global SGD threshold and therefore controls. Director and Finance thresholds are the global SGD equivalents."),
                   C("IN-6.2", "Entertainment approval", "Entertainment above the regional manager threshold requires manager approval of type ENTERTAINMENT or GENERAL."),
                   C("IN-7.1", "Submission window", f"For transactions dated in 2026, a domestic claim must be submitted within {W.IN_SUBMIT_2026} calendar days instead of the global window; claims from day 61 up to and including day 75 require manager approval, and claims after day 75 are escalated to Finance.")]
        if R == "JP":
            cl += [C("JP-2.4", "Alcohol", f"Alcohol is permitted only as part of a client meal or entertainment and may not exceed {W.ALCOHOL['JP'][2024]} percent of the total bill."),
                   C("JP-2.5", "Tips", "Gratuities are not customary and are not reimbursable."),
                   C("JP-4.2", "Rail", "Shinkansen ordinary reserved seating is reimbursable for approved business travel. Green Car requires grade G6 or above or a documented exception."),
                   C("JP-6.1", "Approval thresholds", f"Manager approval is required for any single discretionary expense above {m(W.REGIONAL_MGR['JP'][2024], 'JPY')} for transactions dated in 2024 and 2025 and above {m(W.REGIONAL_MGR['JP'][2026], 'JPY')} for 2026, in local currency, which is stricter than the global SGD threshold and therefore controls."),
                   C("JP-6.2", "Country-manager approval", f"Entertainment above {m(W.JP_ENTERTAIN_COUNTRY_MGR, 'JPY')} in total requires country-manager approval even when the per-attendee amount is within the ceiling. The approval is recorded as an approval of type ENTERTAINMENT at approver level DIRECTOR."),
                   C("JP-8.1", "Hotel cities", "Tokyo uses the Tokyo tier. Osaka, Nagoya and Yokohama use the major-city tier. Other Japanese cities use the other-city tier.")]
        D.append(dict(id=did, key=R, title=f"{name} Expense Addendum", region=R, eff=("2024-01-01", "2099-12-31"), category="regional", rank=2, clauses=cl))
    # ------------------------------------------------ D20 circulars
    D.append(dict(id="D20", key="CIRC", title="Finance Circulars 2024 to 2026", region="GLOBAL", eff=("2024-01-01", "2099-12-31"), category="circular", rank=3,
                  clauses=[C(a["id"], a["title"], f"Effective {a['eff']}. " + circ_text(a)) for a in W.AMEND] +
                  [C("CIRC-REG", "Circular register", "The circulars in force and the clauses they amend:\n\n" + tbl(["Circular", "Effective", "Subject"], [[a["id"], a["eff"], a["title"]] for a in W.AMEND]))]))
    # ------------------------------------------------ D21 historical schedules
    hs = []
    def block(S, label, keys):
        return "\n\n".join(f"{label} {k}: " + ", ".join(f"{y}: {S.base[k][y]:,}" for y in W.YEARS) for k in keys)
    hs.append(C("HIST-1.1", "Published base schedules: meals", "Base values as originally published, before any circular. Later circulars supersede these values from their effective dates.\n\n" + block(W.EMP_MEAL, "Employee meal ceiling", W.EMP_MEAL.keys()) + "\n\n" + block(W.CLIENT_MEAL, "Client meal ceiling", W.CLIENT_MEAL.keys()) + "\n\n" + block(W.ENTERTAIN, "Entertainment ceiling", W.ENTERTAIN.keys())))
    hs.append(C("HIST-1.2", "Published base schedules: gifts, telecom and mileage", "Base values as originally published, before any circular.\n\n" + block(W.GIFT, "Gift ceiling", W.GIFT.keys()) + "\n\n" + block(W.GIFT_ANNUAL, "Annual gift ceiling", W.GIFT_ANNUAL.keys()) + "\n\n" + block(W.TELECOM, "Telecom monthly ceiling", W.TELECOM.keys()) + "\n\n" + block(W.MILEAGE, "Mileage rate", W.MILEAGE.keys())))
    hs.append(C("HIST-1.3", "Published base schedules: hotels", "Base nightly values by year, before any circular.\n\n" + "\n\n".join(f"{loc} {b}: " + ", ".join(f"{y}: {W.HOTEL.base[(loc, b)][y]:,}" for y in W.YEARS) for loc in W._H for b, _, _ in W.BANDS)))
    hs.append(C("HIST-2.1", "Legacy schedule 2023 (expired)", "For information only: the 2023 schedule expired on 31 December 2023 and does not apply to any transaction dated in 2024, 2025 or 2026. Singapore employee meal ceiling per person: SGD 42. Singapore client meal ceiling per attendee: SGD 110. Japan employee meal ceiling per person: JPY 4,200. "
                "India employee meal ceiling per person: INR 1,600. Tokyo nightly ceiling for grade band G4-G5: JPY 30,000. Singapore nightly ceiling for grade band G4-G5: SGD 310. Manager approval threshold: SGD 400 equivalent."))
    hs.append(C("HIST-2.2", "Superseded 2024 drafts", "A draft of the 2025 policy proposed a forty-day submission window and a director threshold of SGD 1,200. The draft was withdrawn and never took effect. It is retained for audit only."))
    hs.append(C("HIST-3.1", "Use of this document", "Values in this document are for locating the base value that applied on a transaction date. They never override a circular that amends them from its effective date."))
    D.append(dict(id="D21", key="HIST", title="Historical Limits and Superseded Schedules", region="GLOBAL", eff=("2024-01-01", "2099-12-31"), category="historical", rank=6, clauses=hs))
    return D
