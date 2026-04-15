#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|_app| {
            // In development, the backend is started separately.
            // In production, launch the sidecar.
            #[cfg(not(debug_assertions))]
            {
                use tauri_plugin_shell::ShellExt;
                let sidecar = _app.shell()
                    .sidecar("zerobox-backend")
                    .expect("failed to create sidecar command");
                let (_rx, _child) = sidecar.spawn()
                    .expect("failed to spawn sidecar");
            }
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
