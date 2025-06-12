"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Loader2 } from "lucide-react";

export default function SubmissionStatusPage() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const arxivId = searchParams.get("arxivId");

    const [status, setStatus] = useState("pending");
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!arxivId) {
            setError("No arXiv ID provided. Redirecting to home...");
            setTimeout(() => router.push("/"), 3000);
            return;
        }

        const pollStatus = async () => {
            try {
                const response = await api.get(`/papers/status/${arxivId}`);
                const currentStatus = response.data.status;
                setStatus(currentStatus);

                if (currentStatus === "completed") {
                    router.push(`/papers/${arxivId}`);
                }
            } catch (err) {
                console.error("Failed to poll status:", err);
                // Stop polling on error
                setError("An error occurred while checking the status.");
            }
        };

        // Start polling immediately and then every 3 seconds
        // as long as the status is not 'completed'.
        pollStatus();
        const intervalId = setInterval(() => {
            setStatus((prevStatus) => {
                if (prevStatus !== "completed") {
                    pollStatus();
                }
                return prevStatus;
            });
        }, 3000);

        return () => clearInterval(intervalId);
    }, [arxivId, router]);

    if (error) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
                <h1 className="text-2xl font-bold text-destructive mb-4">Error</h1>
                <p className="text-muted-foreground">{error}</p>
            </div>
        );
    }

    return (
        <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
            <Loader2 className="h-12 w-12 animate-spin text-primary mb-6" />
            <h1 className="text-2xl font-bold mb-2">Processing Your Submission</h1>
            <p className="text-muted-foreground max-w-md">
                We are fetching, analyzing, and indexing the paper with arXiv ID:{" "}
                <span className="font-mono bg-muted px-1 py-0.5 rounded">
          {arxivId}
        </span>
                .
            </p>
            <p className="text-muted-foreground mt-2">
                You will be redirected automatically when it&apos;s ready.
            </p>
            <div className="mt-4 text-sm font-semibold capitalize">
                Status: <span className="text-primary">{status}...</span>
            </div>
        </div>
    );
}