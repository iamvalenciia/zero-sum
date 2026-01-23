# Zero Sum LDS MCP Server - Setup Guide

## Overview

This MCP (Model Context Protocol) server allows you to create LDS short-form video content directly from Claude Desktop.

### Features
- **create_script**: Generate dialogue scripts with Sister Faith & Brother Marcus
- **search_lds_content**: Search scriptures, prophet quotes, conference talks
- **search_world_news**: Find current events and connect with gospel principles
- **verify_quote**: Verify prophet quotes and scripture references
- **upload_images**: Register manually uploaded images for video assembly
- **generate_audio**: Generate audio using ElevenLabs
- **render_short**: Render 9:16 vertical videos for TikTok/Reels/Shorts

---

## Installation

### 1. Install MCP Dependencies

```bash
cd /home/user/zero-sum
pip install -r lds_mcp/requirements.txt
```

### 2. Configure Claude Desktop

#### Option A: Copy configuration file

1. Open Claude Desktop Settings → Extensions → Open Extension Settings Folder
2. Copy the content from `claude_desktop_config.json` to your Claude Desktop config

#### Option B: Manual configuration

Add this to your Claude Desktop configuration file:

**On macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**On Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
**On Linux:** `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "zero-sum-lds": {
      "command": "python",
      "args": [
        "/home/user/zero-sum/lds_mcp/lds_server.py"
      ],
      "env": {
        "ELEVEN_LABS_API_KEY2": "your-elevenlabs-api-key",
        "GEMINI_API_KEY": "your-gemini-api-key"
      }
    }
  }
}
```

### 3. Set Environment Variables

Make sure these environment variables are set:

```bash
export ELEVEN_LABS_API_KEY2="your-elevenlabs-api-key"
export GEMINI_API_KEY="your-gemini-api-key"
```

### 4. Restart Claude Desktop

After saving the configuration, restart Claude Desktop completely.

---

## Usage

### Creating a Video (Step by Step)

**1. Start with a topic:**
```
Create an LDS short about the importance of daily scripture study
```

**2. Claude will use `create_script` to generate:**
- Dialogue between Sister Faith and Brother Marcus
- Hook text for video overlay
- Pose assignments for characters

**3. Review and approve the script**

**4. Generate audio:**
```
Generate audio for this script
```

**5. Upload images (optional):**
```
I'm uploading images for this video. Here they are:
[drag and drop images to chat]
```

**6. Render the video:**
```
Render the short video with hook text "Why Daily Study Matters"
```

---

## Example Conversations

### Daily Inspiration Video
```
User: Search for news about people finding peace during difficult times,
      and create a short video connecting it with gospel principles.

Claude: [Uses search_world_news + search_lds_content + create_script]
        Here's the script I've created...

User: Looks good! Generate the audio.

Claude: [Uses generate_audio]
        Audio generated successfully.

User: Here are some images I want to use:
      [uploads images]

Claude: [Uses upload_images]
        Images registered. Suggested order based on script:
        1. peaceful_scene.jpg - Opening
        2. family_prayer.jpg - Lines 2-4
        ...

User: Render it with hook text "Finding Peace in Chaos"

Claude: [Uses render_short]
        Video rendered! Output: data/shorts/output/short_video.mp4
```

### Scripture Explanation Video
```
User: Create a short explaining Moroni 10:4 about knowing truth through prayer

Claude: [Uses search_lds_content to get context]
        [Uses create_script with the context]
        Here's the script...
```

---

## Directory Structure

```
data/shorts/
├── scripts/          # Generated JSON scripts
├── audio/            # Generated MP3 audio + timestamps
├── images/           # Manually uploaded images
└── output/           # Final rendered videos
```

---

## Characters

| Character | Role | Voice |
|-----------|------|-------|
| **Sister Faith** | Knowledgeable member who cites prophets, scriptures | Eve (professional) |
| **Brother Marcus** | Curious learner asking sincere questions | Charles (young male) |

---

## Prompts Available

Claude Desktop includes pre-built prompts:

1. **daily_inspiration** - Create inspirational content from current events
2. **scripture_explanation** - Explain a scripture or doctrine
3. **prophet_teaching** - Create content based on prophet's teaching

Use these with: "Use the daily_inspiration prompt about [topic]"

---

## Troubleshooting

### MCP Server not connecting
1. Check that Python path is correct in config
2. Verify all dependencies are installed
3. Check Claude Desktop logs for errors

### Audio generation fails
1. Verify ELEVEN_LABS_API_KEY2 is set correctly
2. Check ElevenLabs API quota

### Quote verification returns "not found"
1. The local database is limited - Claude will suggest web search
2. Use web search for comprehensive verification

---

## Content Guidelines

- Always faith-promoting and positive about the Church
- Only use verified scriptures and prophet quotes
- Never contradict official Church doctrine
- Goal: Build a faithful community of members
