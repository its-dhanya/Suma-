export async function getSaveDialog(options) {
    try {
      if (window.__TAURI_IPC__) {
        // Use string concatenation to avoid static resolution by Vite.
        const { save } = await import("@tauri-apps/api/" + "dialog");
        return await save(options);
      } else {
        return Promise.reject(
          new Error("Tauri API not available. Running outside of Tauri environment.")
        );
      }
    } catch (error) {
      return Promise.reject(error);
    }
  }
  
  export async function writeBinary(path, contents) {
    try {
      if (window.__TAURI_IPC__) {
        // Use string concatenation to avoid static resolution by Vite.
        const { writeBinaryFile } = await import("@tauri-apps/api/" + "fs");
        return await writeBinaryFile(path, contents);
      } else {
        return Promise.reject(
          new Error("Tauri API not available. Running outside of Tauri environment.")
        );
      }
    } catch (error) {
      return Promise.reject(error);
    }
  }