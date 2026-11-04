import { defineConfig, loadEnv, type ProxyOptions } from "vite";
import react from "@vitejs/plugin-react";
import {proxyOriginHeaders} from './proxy-origin.ts';

const apiTarget = loadEnv("development", import.meta.dirname, "FR_DEV_").FR_DEV_API_URL
  || "http://127.0.0.1:8000";

// A temporary HTTPS tunnel can replace Host before reaching this local server.
// Restore only the explicitly configured public origin at the trusted API proxy.
const publicOrigin = process.env.FR_PREVIEW_PUBLIC_ORIGIN;
// Validate once at startup as well as in the tested header helper.
proxyOriginHeaders(undefined, undefined, publicOrigin);
function apiProxy(websocket = false): ProxyOptions {
  return {target: apiTarget, ws: websocket, configure(proxy) {
    const headers = (request: {setHeader(name: string, value: string): unknown}, incoming: {headers: {origin?: string | string[]; host?: string}}) => {
      const origin = typeof incoming.headers.origin === 'string' ? incoming.headers.origin : undefined;
      for (const [key, value] of Object.entries(proxyOriginHeaders(incoming.headers.host, origin, publicOrigin))) request.setHeader(key, value);
    };
    proxy.on('proxyReq', headers);
    proxy.on('proxyReqWs', headers);
  }};
}
const allowedHosts = publicOrigin ? [new URL(publicOrigin).hostname] : undefined;

export default defineConfig({
  plugins: [react()],
  preview: {
    allowedHosts,
    proxy: {
      "/api": apiProxy(true),
      "/health": apiProxy(),
    },
  },
  server: {
    port: 5173,
    strictPort: true,
    allowedHosts,
    proxy: {
      "/api": apiProxy(true),
      "/health": apiProxy()
    }
  }
});
