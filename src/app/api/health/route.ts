import { NextResponse } from "next/server";
import clientPromise from "@/lib/mongodb";

export async function GET() {
  try {
    const client = await clientPromise;
    await client.db().command({ ping: 1 });
    return NextResponse.json({ status: "ok", mongodb: "connected" });
  } catch (error) {
    return NextResponse.json(
      { status: "error", mongodb: "disconnected", detail: String(error) },
      { status: 503 }
    );
  }
}
