"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import api, {ApiPaperBase} from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import { Code } from "lucide-react";
import Link from "next/link";
import {Card, CardContent, CardHeader, CardTitle} from "@/components/ui/card";

interface PaperDetails {
  id: string;
  title: string;
  abstract: string;
  authors: string[];
  contribution: string;
  tasks: string[];
  methods: string[];
  datasets: string[];
  code_links: string[];
}

const InfoSection = ({ title, items }: { title: string; items: string[] }) => {
  if (!items || items.length === 0) return null;
  return (
    <div className="mb-6">
      <h3 className="text-lg font-semibold mb-2">{title}</h3>
      <div className="flex flex-wrap gap-2">
        {items.map((item, index) => (
          <Badge key={index} variant="secondary">
            {item}
          </Badge>
        ))}
      </div>
    </div>
  );
};

export default function PaperDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const [paper, setPaper] = useState<PaperDetails | null>(null);
  const [recommendations, setRecommendations] = useState<ApiPaperBase[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (id) {
      const fetchPaperDetails = async () => {
        try {
          setLoading(true);
          const response = await api.get(`/papers/${id}`);
          setPaper(response.data);
          setError(null);
        } catch (err) {
          console.error("Failed to fetch paper details:", err);
          setError("Failed to load paper. It may not exist.");
        } finally {
          setLoading(false);
        }
      };

      const fetchRecommendations = async () => {
        try {
          const response = await api.get(`/papers/${id}/recommendations`);
          setRecommendations(response.data);
        } catch (err) {
          console.error("Failed to fetch recommendations:", err);
        }
      };

      fetchPaperDetails();
      fetchRecommendations();
    }
  }, [id]);

  if (loading) {
    return <div>Loading paper details...</div>;
  }

  if (error) {
    return <div className="text-red-500">{error}</div>;
  }

  if (!paper) {
    return <div>Paper not found.</div>;
  }

  return (
    <div className="max-w-4xl mx-auto p-4">
      {/* Header Section */}
      <div className="mb-4">
        <h1 className="text-3xl font-bold mb-2">{paper.title}</h1>
        <p className="text-muted-foreground">{paper.authors.join(", ")}</p>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-4 mb-6">
        {paper.code_links && paper.code_links.length > 0 && (
          <a
            href={paper.code_links[0]}
            target="_blank"
            rel="noopener noreferrer"
          >
            <Button>
              <Code className="mr-2 h-4 w-4" /> View Code
            </Button>
          </a>
        )}
      </div>

      <Separator className="my-6" />

      {/* Main Content */}
      <div>
        {paper.contribution && (
          <div className="mb-6">
            <h2 className="text-xl font-semibold mb-2">Main Contribution</h2>
            <blockquote className="border-l-4 pl-4 italic">
              {paper.contribution}
            </blockquote>
          </div>
        )}

        {paper.abstract && (
          <div className="mb-6">
            <h2 className="text-xl font-semibold mb-2">Abstract</h2>
            <p className="text-muted-foreground leading-relaxed">
              {paper.abstract}
            </p>
          </div>
        )}

        <Separator className="my-6" />

        <InfoSection title="Tasks" items={paper.tasks} />
        <InfoSection title="Methods" items={paper.methods} />
        <InfoSection title="Datasets" items={paper.datasets} />
      </div>

      {recommendations.length > 0 && (
          <>
            <Separator className="my-8" />
            <div className="mb-6">
              <h2 className="text-2xl font-semibold mb-4">You Might Also Like</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {recommendations.map((rec) => (
                    <Link href={`/papers/${rec.id}`} key={rec.id}>
                      <Card className="h-full hover:bg-accent">
                        <CardHeader>
                          <CardTitle className="text-base">{rec.title}</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <p className="text-xs text-muted-foreground">{rec.authors.join(", ")}</p>
                        </CardContent>
                      </Card>
                    </Link>
                ))}
              </div>
            </div>
          </>
      )}
    </div>
  );
}
