# Pull Request: Display Now per-image (image_index override)

This branch adds a per-image "Display Now" button to the Image Upload plugin settings and extends the server-side display flow to accept a one-time image_index override.

Summary of changes:
- Client (src/plugins/image_upload/settings.html)
  - Adds a "Display Now" button next to "Set Crop" for saved (existing) images when editing a plugin instance.
  - The button sends a POST to /display_plugin_instance with plugin_id, plugin_instance, and image_index (index of the saved image in the instance settings).
  - The button intentionally does not include unsaved crop changes; it uses saved plugin settings, so the displayed image will reflect the last-saved/cached state.

- Server (src/blueprints/plugin.py)
  - display_plugin_instance now accepts an optional image_index field in the JSON body.
  - When image_index is provided, the server performs a one-off Playlist-like refresh using a temporary copy of the plugin instance settings with the image_index override (the override is not persisted).
  - The generated image is saved to the plugin image path, plugin_instance.latest_refresh_time is updated, device_config is written, and the display manager is asked to display the image.

Behavior and rationale:
- This uses the same path and behavior as the playlist refresh (PlaylistRefresh) for generating, caching, and displaying images, ensuring cached images are used when present and generated+cached when not.
- Unsaved UI crop edits are ignored by this button (per request). The button only appears for saved images.
- The override is temporary for this immediate refresh only, so scheduled or sequential/random playlist behavior is not changed.

Testing checklist:
1. Restart the InkyPi service (to pick up server changes).
2. Open the Image Upload plugin settings in edit mode for a plugin instance.
3. Verify saved images show "Display Now" next to "Set Crop"; newly added images do not show the button.
4. Click "Display Now" on a saved image. It should use the cached processed image if present or generate and cache it if not, and the display should update immediately.
5. Make an unsaved crop change and click "Display Now" — the display should still show the last-saved/cached version, not the unsaved crop.
6. Confirm scheduled updates (playlist/interval/random settings) continue to behave normally.

If you'd like any adjustments (UI text, style, or a different API param name), I can update the branch before merging.
