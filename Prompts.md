trace the process of handling a user's query from frontend to backend.

how do i run this application



# start with - initialize claude.md file.
/init
/ide


# always use uv to run the server do not use pip directly

/help
/clear - clear conversation history
/compact - clear histroy - but keep summary
esc - to get out of command/interrupt

## Referencing correct file
@run.sh
@folder/filename

# Plan Mode. for larger changes
Press shift+tab - to activate plan mode

## Prompt

```

 The chat interface displays query responses with source citations. I need to modify it so each source becomes a clickable link that opens the corresponding lesson video in a new tab:
 - When courses are processed into chunks in @backend/document_processor.py, the link of each lesson is stored in the course_catalog collection
 - Modify format results in abackend/search tools.ov so that the lesson links are also returned
 - The links should be embedded invisibly (no visible URL text)
```

# We can paste screen shots and ask it to make changes. For visual changes.

# New Feature
```
• Add a '+ NEW CHAT' button to the left sidebar above the courses section. When clicked, it should:
 - Clear the current conversation in the chat window
 - Start a new session without page reload
 - Handle proper cleanup on both @frontend and @backend
 - Match the styling of existing sections (Courses, Try asking) - same font size, color, and uppercase
 formating
```
## Tools with mcp
mcp for playwrite

```
claude mcp add playwright npx @playwright/mcp@latest
```

to check
/mcp

Prompt
```
 Using the playwright MCP server visit 127.0.0.1:8000 and view the new chat button. I want that button to
 look the same as the other links below for Courses and Try Asking. Make sure this is left aligned and
 that the border is removed
```

Turn plan mode on.


## Worktrees
mkdir .tree
git worktree add .trees/ui_feature
git worktree add .trees/test_feature
git worktree add .trees/qc_feature
