"use client";

import { useEffect, useState } from "react";
import api from "@/lib/api";
import PaperCard from "@/components/paper-card";
import { useAuth } from "@/context/auth-context";

interface Paper {
  id: string;
  title: string;
  authors: string[];
  publication_year: number;
}

export default function HomePage() {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [bookmarkedIds, setBookmarkedIds] = useState<Set<string>>(new Set());
  const { isAuthenticated } = useAuth();

  const fetchPapers = async () => {
    const response = await api.get("/papers");
    setPapers(response.data);
  };

  const fetchBookmarks = async () => {
    if (isAuthenticated) {
      const response = await api.get("/me/bookmarks");
      const ids = new Set<string>(response.data.map((p: Paper) => p.id));
      setBookmarkedIds(ids);
    } else {
      setBookmarkedIds(new Set());
    }
  };

  useEffect(() => {
    fetchPapers();
  }, []);

  useEffect(() => {
    fetchBookmarks();
  }, [isAuthenticated]);

  const handleBookmarkToggle = (paperId: string) => {
    const newBookmarkedIds = new Set(bookmarkedIds);
    if (newBookmarkedIds.has(paperId)) {
      newBookmarkedIds.delete(paperId);
    } else {
      newBookmarkedIds.add(paperId);
    }
    setBookmarkedIds(newBookmarkedIds);
  };

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Recent Papers</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {papers.map((paper) => (
          <PaperCard
            key={paper.id}
            paper={paper}
            isBookmarked={bookmarkedIds.has(paper.id)}
            onBookmarkToggle={handleBookmarkToggle}
          />
        ))}
      </div>
    </div>
  );
}
