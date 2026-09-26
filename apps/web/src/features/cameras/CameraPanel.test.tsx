import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CameraPanel } from "./CameraPanel";
import type { CameraPublic } from "../../api/contracts";

const camera: CameraPublic = {
  id: "camera-1",
  name: "Entrance",
  source_type: "rtsp",
  rtsp_url: "rtsp://***:***@camera.local/live",
  codec: "AUTO",
  enabled: true,
  sampling_fps: 5,
  lifecycle: "DRAFT",
  revision: "revision-1"
};

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("CameraPanel", () => {
  it("creates an RTSP camera through the API and clears the credential", async () => {
    const requests: Array<{ url: string; init?: RequestInit }> = [];
    let listCount = 0;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      requests.push({ url, init });
      if (url === "/api/v1/cameras" && init?.method === "POST") {
        return Response.json(camera, { status: 201 });
      }
      listCount += 1;
      return Response.json({ items: listCount > 1 ? [camera] : [] });
    }));

    const user = userEvent.setup();
    render(<CameraPanel runtimeStatuses={[]} />);
    await waitFor(() => expect(requests[0]?.url).toBe("/api/v1/cameras"));
    await user.type(screen.getByLabelText("Camera name"), "Entrance");
    const secret = "rtsp://alice:supersecret@camera.local/live";
    await user.type(screen.getByLabelText("RTSP URL"), secret);
    await user.click(screen.getByRole("button", { name: "Add Camera" }));

    await screen.findByText("rtsp://***:***@camera.local/live");
    const create = requests.find((request) => request.init?.method === "POST");
    expect(JSON.parse(String(create?.init?.body))).toMatchObject({
      name: "Entrance",
      rtsp_url: secret,
      codec: "AUTO",
      enabled: true
    });
    expect(screen.queryByDisplayValue(secret)).toBeNull();
  });

  it("edits metadata without sending an empty replacement credential", async () => {
    const requests: Array<{ url: string; init?: RequestInit }> = [];
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      requests.push({ url: String(input), init });
      return init?.method === "PATCH"
        ? Response.json({ ...camera, name: "Lobby" })
        : Response.json({ items: [camera] });
    }));

    const user = userEvent.setup();
    render(<CameraPanel runtimeStatuses={[]} />);
    await screen.findByText("Entrance");
    await user.click(screen.getByRole("button", { name: "Edit" }));
    const name = screen.getByLabelText("Edit name");
    await user.clear(name);
    await user.type(name, "Lobby");
    await user.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => {
      const patch = requests.find((request) => request.init?.method === "PATCH");
      expect(JSON.parse(String(patch?.init?.body))).toEqual({ name: "Lobby", codec: "AUTO" });
    });
  });
});
