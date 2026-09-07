*** Begin Patch
*** Update File: src/blueprints/plugin.py
@@
 @plugin_bp.route('/display_plugin_instance', methods=['POST'])
 def display_plugin_instance():
     device_config = current_app.config['DEVICE_CONFIG']
     refresh_task = current_app.config['REFRESH_TASK']
     playlist_manager = device_config.get_playlist_manager()
 
     data = request.json
     playlist_name = data.get("playlist_name")
     plugin_id = data.get("plugin_id")
     plugin_instance_name = data.get("plugin_instance")
+    image_index = data.get("image_index", None)
 
     try:
-        playlist = playlist_manager.get_playlist(playlist_name)
-        if not playlist:
-            return jsonify({"success": False, "message": f"Playlist {playlist_name} not found"}), 400
-
-        plugin_instance = playlist.find_plugin(plugin_id, plugin_instance_name)
-        if not plugin_instance:
-            return jsonify({"success": False, "message": f"Plugin instance '{plugin_instance_name}' not found"}), 400
-
-        refresh_task.manual_update(PlaylistRefresh(playlist, plugin_instance, force=True))
+        # If playlist_name provided, use it. Otherwise search across playlists for the plugin instance.
+        playlist = None
+        plugin_instance = None
+        if playlist_name:
+            playlist = playlist_manager.get_playlist(playlist_name)
+            if not playlist:
+                return jsonify({"success": False, "message": f"Playlist {playlist_name} not found"}), 400
+            plugin_instance = playlist.find_plugin(plugin_id, plugin_instance_name)
+            if not plugin_instance:
+                return jsonify({"success": False, "message": f"Plugin instance '{plugin_instance_name}' not found in playlist {playlist_name}"}), 400
+        else:
+            # search playlists for the plugin instance
+            for pl in playlist_manager.playlists:
+                pi = pl.find_plugin(plugin_id, plugin_instance_name)
+                if pi:
+                    playlist = pl
+                    plugin_instance = pi
+                    break
+            if not plugin_instance:
+                return jsonify({"success": False, "message": f"Plugin instance '{plugin_instance_name}' not found in any playlist"}), 400
+
+        # Load plugin config and instance plugin class
+        plugin_config = device_config.get_plugin(plugin_id)
+        if not plugin_config:
+            return jsonify({"success": False, "message": f"Plugin '{plugin_id}' not found"}), 404
+
+        plugin = get_plugin_instance(plugin_config)
+
+        # Use a copy of the plugin_instance settings so we do not persist the image_index override
+        temp_settings = dict(plugin_instance.settings) if plugin_instance.settings else {}
+        if image_index is not None:
+            try:
+                temp_settings['image_index'] = int(image_index)
+            except Exception:
+                temp_settings['image_index'] = 0
+
+        # Perform the same work PlaylistRefresh.execute does: generate image, save it to plugin image path,
+        # update latest_refresh_time and write config, and display the image.
+        plugin_image_path = os.path.join(device_config.plugin_image_dir, plugin_instance.get_image_path())
+        os.makedirs(os.path.dirname(plugin_image_path), exist_ok=True)
+
+        from datetime import datetime
+        current_dt = datetime.now()
+        image = plugin.generate_image(temp_settings, device_config)
+        image.save(plugin_image_path)
+        plugin_instance.latest_refresh_time = current_dt.isoformat()
+        device_config.write_config()
+
+        # Display the image via the display manager
+        display_manager = current_app.config.get('DISPLAY_MANAGER')
+        if display_manager:
+            display_manager.display_image(image, image_settings=plugin_config.get("image_settings", []))
*** End Patch
