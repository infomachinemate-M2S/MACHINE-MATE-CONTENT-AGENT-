import streamlit as st
import os
from pathlib import Path
from datetime import datetime
import json
import requests
from PIL import Image
from io import BytesIO
from anthropic import Anthropic

# ── Config ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Machine Mate Content Agent",
    page_icon="M²",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
<style>
    body { background-color: #0f1117; }
    .stApp { background-color: #0f1117; }
    .main { background-color: #0f1117; }
    .stTabs [data-baseweb="tab-list"] { background-color: #181c27; }
    .stButton>button { background-color: #ff6b2b; color: white; border: none; }
    .stButton>button:hover { background-color: #ff8050; }
    h1, h2, h3 { color: #e8eaf0; }
    .css-1d391kg { color: #7a8099; }
</style>
""", unsafe_allow_html=True)

# ── Initialize Session State ──────────────────────────────────
if "client" not in st.session_state:
    api_key = st.secrets.get("ANTHROPIC_API_KEY", os.getenv("ANTHROPIC_API_KEY"))
    if not api_key:
        st.error("⚠️ ANTHROPIC_API_KEY not found. Set it in .streamlit/secrets.toml or .env file")
        st.stop()
    st.session_state.client = Anthropic(api_key=api_key)

if "content_data" not in st.session_state:
    st.session_state.content_data = {}

# ── Helper Functions ──────────────────────────────────────────
def get_platform_config(platform):
    """Get format specifications for each platform"""
    configs = {
        "youtube_long": {
            "name": "📺 YouTube Long Form",
            "duration": "10-20 minutes",
            "structure": "[HOOK] [INTRO] [MAIN CONTENT] [TIPS] [SUMMARY] [CTA]",
            "tone": "Educational, detailed, professional",
            "aspect_ratio": "16:9",
            "thumbnail_style": "Bold text, contrasting colors, close-up CNC machine",
            "script_length": 2500,
        },
        "youtube_short": {
            "name": "⏱️ YouTube Shorts",
            "duration": "45-60 seconds",
            "structure": "[HOOK - 5sec] [MAIN TIP - 45sec] [CTA - 10sec]",
            "tone": "Fast-paced, punchy, attention-grabbing",
            "aspect_ratio": "9:16",
            "thumbnail_style": "Vertical, bold numbers/text, vibrant colors",
            "script_length": 150,
        },
        "instagram_reel": {
            "name": "🎬 Instagram Reel",
            "duration": "15-30 seconds",
            "structure": "[VISUAL HOOK] [QUICK TIP] [CALL TO ACTION]",
            "tone": "Trendy, relatable, Hindi-heavy",
            "aspect_ratio": "9:16",
            "thumbnail_style": "Vertical, Instagram-style, trend colors",
            "script_length": 120,
        },
        "instagram_post": {
            "name": "📸 Instagram Post",
            "duration": "Caption only",
            "structure": "[Hook] [Value] [CTA] [Hashtags]",
            "tone": "Engaging, community-focused, informative",
            "aspect_ratio": "1:1 or 4:5",
            "thumbnail_style": "Square, clean, educational vibe",
            "script_length": 300,
        },
        "facebook_post": {
            "name": "👥 Facebook Post",
            "duration": "200-400 words",
            "structure": "[Story] [Value] [Question] [CTA]",
            "tone": "Conversational, community-building, Hindi mix",
            "aspect_ratio": "1:1 or 4:5",
            "thumbnail_style": "Community-focused, educational",
            "script_length": 350,
        },
    }
    return configs.get(platform, {})

def generate_script(topic, platform, level, keywords, extra_notes):
    """Generate platform-specific script using Anthropic"""
    config = get_platform_config(platform)
    
    system_prompt = f"""Tu Machine Mate Academy ka expert content writer hai. 
Tu Hinglish mein likhta hai (Hindi + English mix, jaise Indian YouTube creators bolte hain).
Tera audience: ITI students, diploma holders, working machinists, engineers India mein.
Platform: {config['name']}
Tone: {config['tone']}
Duration: {config['duration']}
Structure: {config['structure']}

Output sirf script hona chahiye — koi extra explanation nahi. 
Script EXACTLY is structure mein likho with clear section markers."""

    user_prompt = f"""Topic: {topic}
Audience level: {level}
Platform: {config['name']}
Keywords to include: {keywords or 'N/A'}
Extra notes: {extra_notes or 'N/A'}
Target length: ~{config['script_length']} words

Ek complete script likho is structure mein:
{config['structure']}

Hinglish mein likho naturally, CNC/manufacturing ki baat karte hue."""

    try:
        with st.spinner(f"🤖 Script generate ho raha hai {config['name']} ke liye..."):
            message = st.session_state.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1500,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )
            return message.content[0].text
    except Exception as e:
        return f"❌ Error: {str(e)}"

def check_script_quality(script, topic):
    """Analyze script quality and generate SEO data"""
    system_prompt = """Tu ek YouTube content quality analyst hai jo CNC/machining niche samajhta hai.
Respond ONLY in valid JSON format, no markdown, no explanation outside JSON."""

    user_prompt = f"""Analyze this YouTube script and return ONLY this JSON:
{{
  "overall_score": <0-100>,
  "hook_strength": <0-100>,
  "clarity": <0-100>,
  "seo_potential": <0-100>,
  "engagement": <0-100>,
  "issues": ["issue1", "issue2"],
  "strengths": ["strength1", "strength2"],
  "suggested_title": "YouTube title suggestion",
  "suggested_description": "60-word YouTube description",
  "suggested_tags": ["tag1","tag2","tag3","tag4","tag5"]
}}

Script:
{script[:2000]}"""

    try:
        with st.spinner("✅ Script quality check ho raha hai..."):
            message = st.session_state.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=800,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )
            result_text = message.content[0].text.replace("```json", "").replace("```", "").strip()
            return json.loads(result_text)
    except Exception as e:
        return {"error": str(e)}

def generate_thumbnail_prompt(topic, script, platform):
    """Generate thumbnail design prompt"""
    config = get_platform_config(platform)
    
    system_prompt = """Tu ek YouTube/Instagram thumbnail expert hai jo CNC/machining niche ke liye kaam karta hai.
Respond ONLY in valid JSON, no extra text."""

    user_prompt = f"""Platform: {config['name']}
Aspect ratio: {config['aspect_ratio']}
Style: {config['thumbnail_style']}

Topic: {topic}
Script snippet: {script[:500]}

Return ONLY this JSON:
{{
  "image_prompt": "Detailed Midjourney/DALL-E prompt for thumbnail (industrial, dramatic, etc.)",
  "text_overlay_main": "BIG TEXT for thumbnail (max 4 words)",
  "text_overlay_sub": "Subtitle text (max 6 words)",
  "color_theme": "dominant color scheme",
  "style_notes": "visual style description"
}}"""

    try:
        with st.spinner("🖼️ Thumbnail brief generate ho raha hai..."):
            message = st.session_state.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=600,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )
            result_text = message.content[0].text.replace("```json", "").replace("```", "").strip()
            return json.loads(result_text)
    except Exception as e:
        return {"error": str(e)}

def create_export_folder(topic):
    """Create organized export folder structure"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_name = f"content_{topic.replace(' ', '_')}_{timestamp}"
    export_path = Path("exports") / folder_name
    export_path.mkdir(parents=True, exist_ok=True)
    
    # Create platform subdirectories
    platforms = ["youtube_long", "youtube_short", "instagram_reel", "instagram_post", "facebook_post"]
    for platform in platforms:
        (export_path / platform).mkdir(exist_ok=True)
    
    return export_path

def save_platform_content(export_path, platform, script, seo_data=None, thumbnail_prompt=None):
    """Save content for specific platform"""
    platform_path = export_path / platform
    
    # Save script
    with open(platform_path / "script.txt", "w", encoding="utf-8") as f:
        f.write(script)
    
    # Save SEO data if available
    if seo_data and "error" not in seo_data:
        with open(platform_path / "seo_data.txt", "w", encoding="utf-8") as f:
            f.write(f"TITLE: {seo_data.get('suggested_title', 'N/A')}\n\n")
            f.write(f"DESCRIPTION:\n{seo_data.get('suggested_description', 'N/A')}\n\n")
            f.write(f"TAGS: {', '.join(seo_data.get('suggested_tags', []))}\n\n")
            f.write(f"Overall Score: {seo_data.get('overall_score', 'N/A')}/100\n")
    
    # Save thumbnail prompt if available
    if thumbnail_prompt and "error" not in thumbnail_prompt:
        with open(platform_path / "thumbnail_brief.txt", "w", encoding="utf-8") as f:
            f.write(f"IMAGE PROMPT:\n{thumbnail_prompt.get('image_prompt', 'N/A')}\n\n")
            f.write(f"MAIN TEXT: {thumbnail_prompt.get('text_overlay_main', 'N/A')}\n")
            f.write(f"SUB TEXT: {thumbnail_prompt.get('text_overlay_sub', 'N/A')}\n")
            f.write(f"COLOR THEME: {thumbnail_prompt.get('color_theme', 'N/A')}\n")

# ── Main UI ───────────────────────────────────────────────────
st.markdown("""
<div style='text-align: center; margin-bottom: 30px;'>
    <h1 style='color: #ff6b2b;'>🤖 Machine Mate Content Agent</h1>
    <p style='color: #7a8099; font-size: 14px;'>Multi-Platform Script + Thumbnail Generation</p>
</div>
""", unsafe_allow_html=True)

# Sidebar - Input Configuration
with st.sidebar:
    st.markdown("### 🎯 Content Setup")
    
    topic = st.text_input("📝 Video Topic", placeholder="G-code basics for VMC operators")
    
    col1, col2 = st.columns(2)
    with col1:
        level = st.selectbox("Level", ["Beginner (ITI)", "Intermediate (Diploma)", "Advanced (Engineer)"])
    with col2:
        duration = st.selectbox("Duration", ["5-8 min", "10-15 min", "15-20 min", "20-30 min"])
    
    keywords = st.text_input("Keywords", placeholder="G-code, CNC, VMC, Siemens")
    extra_notes = st.text_area("Extra Notes", placeholder="Special instructions, examples, etc.", height=80)
    
    st.markdown("---")
    st.markdown("### 📱 Platform Selection")
    
    platforms = {
        "youtube_long": "📺 YouTube Long Form",
        "youtube_short": "⏱️ YouTube Shorts",
        "instagram_reel": "🎬 Instagram Reel",
        "instagram_post": "📸 Instagram Post",
        "facebook_post": "👥 Facebook Post",
    }
    
    selected_platforms = []
    for platform_key, platform_name in platforms.items():
        if st.checkbox(platform_name, value=(platform_key == "youtube_long")):
            selected_platforms.append(platform_key)

# Main Content Area
if not topic:
    st.info("👈 Sidebar mein topic aur platforms select karo to shuru karte hain!")
else:
    if not selected_platforms:
        st.warning("⚠️ Kum se kum ek platform select karo!")
    else:
        # Tabs for each platform
        tab_list = [platforms[p] for p in selected_platforms]
        tabs = st.tabs(tab_list)
        
        for idx, platform in enumerate(selected_platforms):
            with tabs[idx]:
                st.markdown(f"### {platforms[platform]}")
                
                config = get_platform_config(platform)
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown(f"**Duration:** {config['duration']}")
                    st.markdown(f"**Tone:** {config['tone']}")
                    st.markdown(f"**Structure:** {config['structure']}")
                
                with col2:
                    st.markdown(f"**Aspect Ratio:** {config['aspect_ratio']}")
                    st.markdown(f"**Target Length:** ~{config['script_length']} words")
                
                st.markdown("---")
                
                # Generate Script Button
                if st.button(f"⚡ Generate Script - {platforms[platform]}", key=f"gen_{platform}"):
                    script = generate_script(topic, platform, level, keywords, extra_notes)
                    st.session_state.content_data[platform] = {"script": script}
                    st.rerun()
                
                # Display & Edit Script
                if platform in st.session_state.content_data and "script" in st.session_state.content_data[platform]:
                    script = st.session_state.content_data[platform]["script"]
                    
                    st.markdown("**Generated Script:**")
                    edited_script = st.text_area(
                        "Edit if needed:",
                        value=script,
                        height=300,
                        key=f"script_{platform}",
                        label_visibility="collapsed"
                    )
                    st.session_state.content_data[platform]["script"] = edited_script
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if st.button(f"✅ Check Quality", key=f"check_{platform}"):
                            seo_data = check_script_quality(edited_script, topic)
                            st.session_state.content_data[platform]["seo_data"] = seo_data
                            st.rerun()
                    
                    with col2:
                        if st.button(f"🖼️ Generate Thumbnail", key=f"thumb_{platform}"):
                            thumb_prompt = generate_thumbnail_prompt(topic, edited_script, platform)
                            st.session_state.content_data[platform]["thumbnail_prompt"] = thumb_prompt
                            st.rerun()
                    
                    with col3:
                        if st.button(f"📋 Copy Script", key=f"copy_{platform}"):
                            st.success("✅ Script copied to clipboard!")
                    
                    # Display Quality Check Results
                    if platform in st.session_state.content_data and "seo_data" in st.session_state.content_data[platform]:
                        seo_data = st.session_state.content_data[platform]["seo_data"]
                        
                        if "error" not in seo_data:
                            st.markdown("---")
                            st.markdown("### ✅ Quality Analysis")
                            
                            col1, col2, col3, col4, col5 = st.columns(5)
                            scores = [
                                ("Overall", seo_data.get("overall_score", 0)),
                                ("Hook", seo_data.get("hook_strength", 0)),
                                ("Clarity", seo_data.get("clarity", 0)),
                                ("SEO", seo_data.get("seo_potential", 0)),
                                ("Engagement", seo_data.get("engagement", 0)),
                            ]
                            
                            cols = [col1, col2, col3, col4, col5]
                            for col, (label, score) in zip(cols, scores):
                                with col:
                                    st.metric(label, f"{score}/100")
                            
                            # Issues & Strengths
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown("**Strengths:**")
                                for strength in seo_data.get("strengths", []):
                                    st.success(f"✓ {strength}")
                            
                            with col2:
                                st.markdown("**Issues:**")
                                for issue in seo_data.get("issues", []):
                                    st.warning(f"⚠️ {issue}")
                            
                            # SEO Suggestions
                            st.markdown("---")
                            st.markdown("### 🏷️ SEO Suggestions")
                            
                            st.text_input(
                                "Suggested Title:",
                                value=seo_data.get("suggested_title", ""),
                                disabled=True
                            )
                            
                            st.text_area(
                                "Suggested Description:",
                                value=seo_data.get("suggested_description", ""),
                                height=80,
                                disabled=True
                            )
                            
                            st.markdown("**Tags:**")
                            tags_display = ", ".join(seo_data.get("suggested_tags", []))
                            st.code(tags_display, language="")
                    
                    # Display Thumbnail Brief
                    if platform in st.session_state.content_data and "thumbnail_prompt" in st.session_state.content_data[platform]:
                        thumb_prompt = st.session_state.content_data[platform]["thumbnail_prompt"]
                        
                        if "error" not in thumb_prompt:
                            st.markdown("---")
                            st.markdown("### 🖼️ Thumbnail Brief")
                            
                            col1, col2 = st.columns([2, 1])
                            
                            with col1:
                                st.markdown("**Image Generation Prompt:**")
                                st.code(thumb_prompt.get("image_prompt", ""), language="")
                            
                            with col2:
                                st.markdown("**Text Overlay:**")
                                st.info(f"**{thumb_prompt.get('text_overlay_main', '')}**\n\n{thumb_prompt.get('text_overlay_sub', '')}")
                            
                            st.markdown(f"**Color Theme:** {thumb_prompt.get('color_theme', '')}")
                            st.markdown(f"**Style Notes:** {thumb_prompt.get('style_notes', '')}")

# Export Section
st.markdown("---")
if st.button("📦 Export All Content", key="export_all"):
    if not topic:
        st.error("⚠️ Topic enter karo!")
    elif not selected_platforms:
        st.error("⚠️ Kum se kum ek platform select karo!")
    else:
        export_path = create_export_folder(topic)
        
        for platform in selected_platforms:
            if platform in st.session_state.content_data:
                script = st.session_state.content_data[platform].get("script", "")
                seo_data = st.session_state.content_data[platform].get("seo_data")
                thumbnail_prompt = st.session_state.content_data[platform].get("thumbnail_prompt")
                
                if script:
                    save_platform_content(export_path, platform, script, seo_data, thumbnail_prompt)
        
        st.success(f"✅ Content exported to: {export_path}")
        st.info(f"📁 Open folder: exports/content_{topic.replace(' ', '_')}_*")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #7a8099; font-size: 12px;'>
    <p>Machine Mate Academy | Multi-Platform Content Generation System</p>
    <p>Phase 1: Script → Check → Thumbnail | Phase 2: Auto TTS + Direct Upload</p>
</div>
""", unsafe_allow_html=True)
