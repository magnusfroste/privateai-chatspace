# Workspace Settings Component

## Overview
There is **ONE** workspace settings component in the application using a sidebar pattern for consistency with Notes and Documents.

## Component

### WorkspaceSettingsSidebar.tsx
- **Location**: `src/components/WorkspaceSettingsSidebar.tsx`
- **Type**: Collapsible sidebar
- **Usage**: Slides in from the right side
- **Trigger**: `showSettingsSidebar` state in Chat.tsx (Settings button in topbar)
- **Layout**: Expandable sidebar (256px collapsed, 800px expanded)

## Design Decision
The modal version (WorkspaceSettings.tsx) was removed to maintain UI consistency:
- Notes = Sidebar
- Documents = Sidebar  
- Settings = Sidebar

This provides a consistent interaction pattern and allows users to keep settings open while chatting.

## Important Notes

⚠️ **When adding new workspace settings:**
1. Add the field to WorkspaceSettingsSidebar.tsx
2. Update state management (useState)
3. Update the API call in `handleSave` function
4. Update the `useEffect` sync logic to sync with workspace prop changes

## Current Settings Fields
- name
- description
- system_prompt
- rag_mode (global/precise/comprehensive)
- use_reranking (boolean)
- rerank_top_k (number, 5-50)

## Backend Integration
Both components use:
- `api.workspaces.update()` from `src/lib/api.ts`
- Workspace interface from `src/lib/api.ts`
- Backend endpoint: `PUT /api/workspaces/{id}`
