import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  env: {
    // Railway backend URL — hardcoded for production
    NEXT_PUBLIC_API_URL: "https://slops-hackathon-project-production.up.railway.app",
  },
};

export default nextConfig;
