import os
import json
import time
import requests
import streamlit as st

# -----------------------------
# Config
# -----------------------------
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
APP_NAME = "Humanet"
ICON_PATH = os.getenv("ICON_PATH", "icon.png")  # optional local icon

st.set_page_config(
    page_title=f"{APP_NAME} – Civic & SDG Platform",
    page_icon=ICON_PATH if os.path.exists(ICON_PATH) else "🌍",
    layout="wide"
)

# -----------------------------
# Helpers
# -----------------------------
def api_get(path, params=None, token=None):
    headers = {"accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.get(f"{BACKEND_URL}{path}", params=params, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()

def api_post(path, payload=None, token=None):
    headers = {"accept": "application/json", "Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.post(f"{BACKEND_URL}{path}", data=json.dumps(payload or {}), headers=headers, timeout=60)
    r.raise_for_status()
    return r.json()

def require_auth():
    if "token" not in st.session_state or not st.session_state.token:
        st.warning("Please log in first.")
        st.stop()

def badge(text):
    st.markdown(
        f"<span style='background:#EEF5FF;border:1px solid #CFE2FF;color:#0A58CA;"
        f"padding:2px 8px;border-radius:12px;font-size:12px'>{text}</span>",
        unsafe_allow_html=True
    )

# -----------------------------
# Session init
# -----------------------------
if "token" not in st.session_state:
    st.session_state.token = None
if "role" not in st.session_state:
    st.session_state.role = None
if "email" not in st.session_state:
    st.session_state.email = None
if "name" not in st.session_state:
    st.session_state.name = None
if "location" not in st.session_state:
    st.session_state.location = None
if "age" not in st.session_state:
    st.session_state.age = None
if "ngo_goals" not in st.session_state:
    st.session_state.ngo_goals = None

# -----------------------------
# Header
# -----------------------------
cols = st.columns([1, 6, 3])
with cols[0]:
    if os.path.exists(ICON_PATH):
        st.image(ICON_PATH, width=48)
    else:
        st.write("🌍")
with cols[1]:
    st.markdown(f"### {APP_NAME}")
    st.caption("Civic reports, SDG surveys, SkillUp tutorials, NGO insights — in one place.")
with cols[2]:
    if st.session_state.token:
        badge(f"Logged in as {st.session_state.role}")
        st.write(st.session_state.email or "")
        if st.button("Logout", use_container_width=True):
            st.session_state.token = None
            st.session_state.role = None
            st.session_state.email = None
            st.experimental_rerun()

st.divider()

# -----------------------------
# Auth Panel
# -----------------------------
with st.expander("Sign up / Login", expanded=(st.session_state.token is None)):
    auth_mode = st.radio("Choose Action", ["Login", "Sign up"], horizontal=True)

    if auth_mode == "Sign up":
        role = st.selectbox("Account type", ["Individual", "NGO"])
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Full name / NGO name", placeholder="Jane Doe / SaveWater Org")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
        with col2:
            location = st.text_input("Location (City, Country)", placeholder="Kampala, Uganda")
            age = st.number_input("Age (Individuals only)", min_value=10, max_value=120, value=25, step=1)
            goals = st.text_area("NGO Goals (NGO only)", placeholder="Our mission is to ...") if role == "NGO" else ""

        if st.button("Create account", type="primary"):
            try:
                payload = {
                    "email": email.strip(),
                    "password": password,
                    "role": role,
                    "name": name.strip(),
                    "age": int(age) if role == "Individual" else None,
                    "location": location.strip(),
                    "goals": goals.strip() if role == "NGO" else None
                }
                data = api_post("/auth/register", payload)
                st.session_state.token = data["access_token"]
                st.session_state.role = role
                st.session_state.email = email.strip()
                st.session_state.name = name.strip()
                st.session_state.location = location.strip()
                st.session_state.age = int(age) if role == "Individual" else None
                st.session_state.ngo_goals = goals.strip() if role == "NGO" else None
                st.success("Account created & logged in.")
                time.sleep(0.6)
                st.experimental_rerun()
            except requests.HTTPError as e:
                st.error(f"Sign up failed: {e.response.text}")

    else:  # Login
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pwd")
        if st.button("Login", type="primary"):
            try:
                data = api_post("/auth/login", {"email": email.strip(), "password": password})
                # We don't know role from token; keep minimal header
                st.session_state.token = data["access_token"]
                st.session_state.email = email.strip()
                st.success("Logged in.")
                time.sleep(0.5)
                st.experimental_rerun()
            except requests.HTTPError as e:
                st.error(f"Login failed: {e.response.text}")

# If not logged in, stop here
if not st.session_state.token:
    st.stop()

# -----------------------------
# Main Navigation
# -----------------------------
tabs = st.tabs([
    "Surveys", "Civic Reports", "SkillUp", "Discussions",
    "NGO AI Report", "Profile"
])

# -----------------------------
# Surveys
# -----------------------------
with tabs[0]:
    st.subheader("Surveys")
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("##### Find Surveys Where You Are")
        my_loc = st.text_input("Your location", value=st.session_state.location or "")
        if st.button("List surveys", key="list_surveys_btn"):
            try:
                res = api_get("/surveys/list", params={"location": my_loc}, token=st.session_state.token)
                if not res:
                    st.info("No surveys found for that location.")
                else:
                    for s in res:
                        with st.container(border=True):
                            st.write(f"**{s['title']}** (SDG {s['sdg']})")
                            st.caption(f"Target: {s['target_location']}")
                            st.code("\n".join([f"Q{i+1}: {q}" for i, q in enumerate(s['questions'])]))
                            with st.form(f"resp_{s['id']}"):
                                st.markdown("**Your Answers**")
                                answers = {}
                                for i, q in enumerate(s["questions"]):
                                    answers[i] = st.text_area(q, key=f"ans_{s['id']}_{i}")
                                submitted = st.form_submit_button("Submit Answers")
                                if submitted:
                                    try:
                                        out = api_post(f"/surveys/{s['id']}/respond",
                                                       {"answers": answers},
                                                       token=st.session_state.token)
                                        st.success("Submitted. Thank you!")
                                    except requests.HTTPError as e:
                                        st.error(f"Submit failed: {e.response.text}")
            except requests.HTTPError as e:
                st.error(f"List failed: {e.response.text}")

    with c2:
        st.markdown("##### Create Survey (NGOs)")
        st.caption("Only visible to NGOs.")
        # We attempt the endpoint and rely on backend permissions
        with st.form("create_survey_form"):
            title = st.text_input("Title")
            description = st.text_area("Description")
            sdg = st.number_input("SDG Number (1-17)", min_value=1, max_value=17, value=4)
            target_location = st.text_input("Target Location", value="Uganda")
            questions_blob = st.text_area("Questions (one per line)")
            submit_create = st.form_submit_button("Create Survey")
        if submit_create:
            try:
                questions = [q.strip() for q in questions_blob.splitlines() if q.strip()]
                payload = {
                    "title": title.strip(),
                    "description": description.strip(),
                    "sdg": int(sdg),
                    "target_location": target_location.strip(),
                    "questions": questions
                }
                out = api_post("/surveys/create", payload, token=st.session_state.token)
                st.success(f"Survey created. ID: {out.get('survey_id')}")
            except requests.HTTPError as e:
                st.error(f"Create failed: {e.response.text}")

# -----------------------------
# Civic Reports
# -----------------------------
with tabs[1]:
    st.subheader("Civic Reports (Disasters, Crimes, Achievements, SDG progress)")
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("##### Publish a Report")
        with st.form("civic_report_form"):
            category = st.selectbox("Category", ["disaster", "crime", "achievement", "sdg"])
            title = st.text_input("Title")
            content = st.text_area("Details")
            location = st.text_input("Location", value=st.session_state.location or "")
            submit_report = st.form_submit_button("Submit")
        if submit_report:
            try:
                out = api_post("/civic/report", {
                    "category": category,
                    "title": title.strip(),
                    "content": content.strip(),
                    "location": location.strip()
                }, token=st.session_state.token)
                ok = "✅ Verified human" if out.get("verified") else "⚠️ Needs review"
                st.success(f"Report stored (ID {out.get('id')}). {ok}")
            except requests.HTTPError as e:
                st.error(f"Submit failed: {e.response.text}")

    with c2:
        st.markdown("##### Local Feed")
        f_loc = st.text_input("Filter by location (optional)", value=st.session_state.location or "")
        f_cat = st.selectbox("Filter by category", ["", "disaster", "crime", "achievement", "sdg"])
        if st.button("Load feed"):
            try:
                res = api_get("/civic/feed", params={"location": f_loc, "category": f_cat}, token=st.session_state.token)
                if not res:
                    st.info("No recent reports.")
                for r in res:
                    with st.container(border=True):
                        st.write(f"**{r['title']}** — {r['category'].upper()}")
                        st.caption(f"{r['location']} • {r['created_at']}")
                        badge("Verified" if r.get("verified") else "Unverified")
            except requests.HTTPError as e:
                st.error(f"Load failed: {e.response.text}")

# -----------------------------
# SkillUp
# -----------------------------
with tabs[2]:
    st.subheader("SkillUp — Tutorials & NGO Opportunities")
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("##### Post a Tutorial (any user)")
        with st.form("tutorial_form"):
            t_title = st.text_input("Title", key="t_title")
            t_content = st.text_area("Content", key="t_content")
            t_tags = st.text_input("SDG Tags (comma-separated)", key="t_tags")
            t_loc = st.text_input("Location", value=st.session_state.location or "", key="t_loc")
            btn_tut = st.form_submit_button("Publish Tutorial")
        if btn_tut:
            try:
                out = api_post("/skillup/tutorials/create", {
                    "title": t_title.strip(),
                    "content": t_content.strip(),
                    "sdg_tags": t_tags.strip(),
                    "location": t_loc.strip()
                }, token=st.session_state.token)
                st.success(f"Tutorial created. ID: {out.get('tutorial_id')}")
            except requests.HTTPError as e:
                st.error(f"Create failed: {e.response.text}")

        st.markdown("##### Browse Tutorials")
        ft_tag = st.text_input("Filter by SDG tag (optional)")
        ft_loc = st.text_input("Filter by location (optional)", value=st.session_state.location or "")
        if st.button("Load tutorials"):
            try:
                res = api_get("/skillup/tutorials", params={"tag": ft_tag, "location": ft_loc}, token=st.session_state.token)
                if not res:
                    st.info("No tutorials found.")
                for t in res:
                    with st.container(border=True):
                        st.write(f"**{t['title']}**")
                        st.caption(f"{t.get('sdg_tags') or 'No tags'} • {t.get('location') or '—'}")
            except requests.HTTPError as e:
                st.error(f"Load failed: {e.response.text}")

    with c2:
        st.markdown("##### Post Volunteer Opportunity (NGO only)")
        with st.form("opp_form"):
            o_title = st.text_input("Title", key="o_title")
            o_details = st.text_area("Details", key="o_details")
            o_loc = st.text_input("Location", value=st.session_state.location or "", key="o_loc")
            o_tags = st.text_input("SDG Tags (comma-separated)", key="o_tags")
            btn_opp = st.form_submit_button("Create Opportunity")
        if btn_opp:
            try:
                out = api_post("/skillup/opportunities/create", {
                    "title": o_title.strip(),
                    "details": o_details.strip(),
                    "location": o_loc.strip(),
                    "sdg_tags": o_tags.strip()
                }, token=st.session_state.token)
                st.success(f"Opportunity created. ID: {out.get('opportunity_id')}")
            except requests.HTTPError as e:
                st.error(f"Create failed: {e.response.text}")

        st.markdown("##### Browse Opportunities")
        fo_loc = st.text_input("Filter by location", value=st.session_state.location or "", key="fo_loc")
        if st.button("Load opportunities"):
            try:
                res = api_get("/skillup/opportunities", params={"location": fo_loc}, token=st.session_state.token)
                if not res:
                    st.info("No opportunities found.")
                for o in res:
                    with st.container(border=True):
                        st.write(f"**{o['title']}**")
                        st.caption(f"{o.get('sdg_tags') or 'No tags'} • {o['location']}")
            except requests.HTTPError as e:
                st.error(f"Load failed: {e.response.text}")

# -----------------------------
# Discussions
# -----------------------------
# -----------------------------
# Discussion Layer
# -----------------------------
with tabs[3]:
    st.subheader("Community Discussions")
    st.caption("Post a topic and share views with others.")

    # Create new topic
    with st.form("new_topic_form"):
        title = st.text_input("Topic Title")
        content = st.text_area("Topic Content")
        submit = st.form_submit_button("Post Topic")
    if submit:
        try:
            out = api_post("/discussions/new", {
                "title": title.strip(),
                "content": content.strip()
            }, token=st.session_state.token)
            st.success(f"Topic created with ID: {out.get('topic_id')}")
        except requests.HTTPError as e:
            st.error(f"Topic creation failed: {e.response.text}")

    # Fetch & display topics
    try:
        topics = api_post("/discussions/list", {}, token=st.session_state.token).get("topics", [])
        for t in topics:
            with st.expander(t["title"]):
                st.write(t["content"])
                st.caption(f"By: {t['author']} | {t['created_at']}")

                # Comment form
                with st.form(f"comment_form_{t['id']}"):
                    body = st.text_input("Add a comment", key=f"comment_{t['id']}")
                    submit_comment = st.form_submit_button("Post Comment")
                if submit_comment:
                    try:
                        out = api_post("/discussions/comment", {
                            "topic_id": t["id"],
                            "body": body.strip()
                        }, token=st.session_state.token)
                        st.success(f"Comment added. ID: {out.get('comment_id')}")
                    except requests.HTTPError as e:
                        st.error(f"Comment failed: {e.response.text}")
    except requests.HTTPError as e:
        st.error(f"Failed to load discussions: {e.response.text}")

# -----------------------------
# NGO AI Report
# -----------------------------
with tabs[4]:
    st.subheader("NGO AI Report (Survey Insights)")
    st.caption("Generate a quick summary over survey responses.")
    with st.form("ai_report_form"):
        survey_id = st.number_input("Survey ID", min_value=1, step=1)
        region = st.text_input("Region filter (optional)", placeholder="e.g., East Africa")
        btn = st.form_submit_button("Generate Report")
    if btn:
        try:
            res = api_post("/reports/ai-summary", {"survey_id": int(survey_id), "region": region or None},
                           token=st.session_state.token)
            st.success(f"Responses analyzed: {res.get('count', '—')}")
            st.text_area("Summary", value=res.get("summary", ""), height=220)
        except requests.HTTPError as e:
            st.error(f"Report failed: {e.response.text}")

# -----------------------------
# Profile
# -----------------------------
with tabs[5]:
    st.subheader("Profile")
    st.write(f"**Email:** {st.session_state.email or ''}")
    st.write(f"**Role:** {st.session_state.role or '—'}")
    st.write(f"**Name:** {st.session_state.name or '—'}")
    st.write(f"**Location:** {st.session_state.location or '—'}")
    if st.session_state.role == "Individual":
        st.write(f"**Age:** {st.session_state.age or '—'}")
    if st.session_state.role == "NGO":
        st.write(f"**NGO Goals:** {st.session_state.ngo_goals or '—'}")

st.caption("© Humanet prototype")