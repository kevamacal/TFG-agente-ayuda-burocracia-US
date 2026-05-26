import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest, { params }: { params: { path: string[] } }) {
  return handleProxy(request, params.path);
}

export async function POST(request: NextRequest, { params }: { params: { path: string[] } }) {
  return handleProxy(request, params.path);
}

export async function PUT(request: NextRequest, { params }: { params: { path: string[] } }) {
  return handleProxy(request, params.path);
}

export async function DELETE(request: NextRequest, { params }: { params: { path: string[] } }) {
  return handleProxy(request, params.path);
}

async function handleProxy(request: NextRequest, pathSegments: string[]) {
  const backendUrl = process.env.API_URL || "http://localhost:8000";
  const path = pathSegments.join("/");
  
  // Reconstruct query parameters
  const { search } = new URL(request.url);
  const targetUrl = `${backendUrl}/${path}${search}`;

  const headers = new Headers(request.headers);
  // Remove host header to avoid SSL/Routing conflicts at Cloudflare/Render load balancers
  headers.delete("host");

  try {
    const body = request.method !== "GET" && request.method !== "HEAD" 
      ? await request.arrayBuffer() 
      : undefined;

    const response = await fetch(targetUrl, {
      method: request.method,
      headers: headers,
      body: body,
      cache: "no-store",
    });

    // Check if the response is SSE stream (for the chat endpoint)
    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("text/event-stream")) {
      return new NextResponse(response.body, {
        status: response.status,
        headers: response.headers,
      });
    }

    const responseBody = await response.arrayBuffer();
    return new NextResponse(responseBody, {
      status: response.status,
      headers: response.headers,
    });
  } catch (error: any) {
    console.error("Proxy connection error:", error);
    // Extract underlying cause if it exists (e.g. connection refused, timeout, dns lookup failed)
    const cause = error.cause || {};
    const causeDetails = {
      message: cause.message || null,
      code: cause.code || null,
      address: cause.address || null,
      port: cause.port || null,
    };
    return new NextResponse(
      JSON.stringify({ 
        detail: "Proxy connection error", 
        error: error.message,
        cause: causeDetails 
      }), 
      {
        status: 502,
        headers: { "Content-Type": "application/json" },
      }
    );
  }
}

