# CameraFly UI Improvement Plan

## Current Issues

1. **UI Clutter**
   - The interface still contains too much information in some sections
   - Some elements are repeated across different tabs
   - Layout could be more streamlined and focused

2. **Missing Information**
   - ALT key for changing rotation mode is not documented
   - Some shortcuts and controls need better explanations
   - Relationships between controls are not always clear

3. **Organization Issues**
   - Aim control is currently in the rotation tab but belongs in the movement tab
   - Some logically related controls are separated

## Proposed Improvements

### 1. Restructure Tabs

| Current Tab Structure | Proposed Tab Structure |
|----------------------|------------------------|
| Movement             | General Movement       |
| Rotation             | Camera Controls        |
| Animation            | Animation              |
| Settings             | Settings               |

### 2. Content Redistribution

#### General Movement Tab
- Standard movement controls (WASD, EQ)
- **Move aim bone controls (mouse wheel)** - *Relocated from Rotation tab*
- Aim distance step settings
- Movement speed controls

#### Camera Controls Tab
- Yaw/pitch rotation via mouse movement
- Rotation speed settings
- **Rotation mode toggle (AIM/CAMERA)** - *Add ALT shortcut info*
- Visual indicator for current rotation mode

#### Animation Tab
- Keyframing controls
- Visual keyframe type indicator
- Simplified keyframe mode selection

#### Settings Tab
- All numerical properties in one place
- Rotation mode selection with detailed explanations
- Help and informational links

### 3. Streamlining UI Elements

1. **Consistent Layout Patterns**
   - Use standard spacing between elements
   - Maintain consistent labeling patterns
   - Group related controls in collapsed sections when possible

2. **Reduce Repetition**
   - Remove duplicate information
   - Use icons more effectively to reduce text
   - Replace text-heavy descriptions with tooltips

3. **Visual Hierarchy**
   - More prominent primary actions
   - Subdued secondary information
   - Clear visual separation between sections

### 4. Specific UI Components to Improve

#### Header Area
- Simpler status indicator
- Camera selection in a dropdown menu
- Quick-access shortcut summary

#### Shortcuts Documentation
- Create a dedicated "Help" button that expands to show all shortcuts
- Document ALT key for rotation mode switch
- Group shortcuts by function rather than by key

#### Action Buttons
- Larger, more prominent activation button
- Group related actions together
- Use consistent action button styling

## Implementation Details

### Tab Changes
1. Reorganize `panels.py` tab content to match the new structure
2. Move the aim bone controls from rotation tab to movement tab
3. Add ALT shortcut documentation for rotation mode switching

### Layout Improvements
1. Reduce box nesting to minimum necessary level
2. Use consistent factors for split layouts (0.4)
3. Ensure proper vertical spacing between groups
4. Implement collapsible sections for less frequently used options

### Visual Design
1. Use more consistent iconography
2. Implement subtle color coding for different functional areas
3. Improve contrast between interactive and informational elements

## UI Code Structure Improvements
1. Extract common UI patterns into reusable functions
2. Create dedicated functions for each tab's content
3. Implement conditional display based on context
4. Add proper tooltips throughout the interface

This plan addresses all the issues while maintaining the core functionality and improving the overall user experience with the CameraFly add-on.
