"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/auth-context";
import api from "@/lib/api";
import PaperCard from "@/components/paper-card";

interface Paper {
  id: string;
  title: string;
  authors: string[];
  publication_year: number;
}

export default function LibraryPage() {
  const { isAuthenticated, user } = useAuth();
  const router = useRouter();
  const [bookmarkedPapers, setBookmarkedPapers] = useState<Paper[]>([]);

  useEffect(() => {
    if (!localStorage.getItem("token")) {
      router.push("/login");
      return;
    }

    const fetchMyBookmarks = async () => {
      try {
        const response = await api.get("/me/bookmarks");
        setBookmarkedPapers(response.data);
      } catch (error) {
        console.error("Failed to fetch bookmarks", error);
      }
    };

    fetchMyBookmarks();
  }, [isAuthenticated, router]);

  const handleBookmarkToggle = (paperId: string) => {
    // Remove the paper from the list visually when unbookmarked
    setBookmarkedPapers((prev) => prev.filter((p) => p.id !== paperId));
  };

  if (!user) {
    return <div>Loading...</div>;
  }

  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">My Library</h1>
      {bookmarkedPapers.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {bookmarkedPapers.map((paper) => (
            <PaperCard
              key={paper.id}
              paper={paper}
              isBookmarked={true}
              onBookmarkToggle={handleBookmarkToggle}
            />
          ))}
        </div>
      ) : (
        <p>You haven&apos;t bookmarked any papers yet.</p>
      )}
    </div>
  );
}
