import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";

// https://vitejs.dev/config/
export default defineConfig(async ({ mode }) => {
  const plugins: any[] = [react()];

  if (mode === "development") {
    try {
      const { componentTagger } = await import("lovable-tagger");
      plugins.push(componentTagger());
    } catch (err) {
      // If lovable-tagger isn't installed or fails to load, continue without it
    }
  }

  return {
    server: {
      host: "::",
      port: 8080,
      proxy: {
        "/api": {
          target: process.env.VITE_API_PROXY_TARGET || "http://localhost:8000",
          changeOrigin: true,
          ws: true,
        },
      },
    },
    plugins,
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
  };
});
