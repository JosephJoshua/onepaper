"use client";

import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Bookmark } from "lucide-react";
import { toast } from "sonner";
import api from "@/lib/api";
import { useAuth } from "@/context/auth-context";

interface Paper {
  id: string;
  title: string;
  authors: string[];
}

interface PaperCardProps {
  paper: Paper;
  isBookmarked: boolean;
  onBookmarkToggle: (paperId: string) => void;
}

export default function PaperCard({
  paper,
  isBookmarked,
  onBookmarkToggle,
}: PaperCardProps) {
  const { isAuthenticated } = useAuth();

  const handleBookmark = async () => {
    if (!isAuthenticated) {
      toast.error("Please log in to bookmark papers");
      return;
    }
    try {
      if (isBookmarked) {
        await api.delete(`/papers/${paper.id}/bookmark`);
        toast.success("Bookmark removed");
      } else {
        await api.post(`/papers/${paper.id}/bookmark`);
        toast.success("Bookmark added");
      }
      onBookmarkToggle(paper.id);
    } catch (error) {
      console.error("Bookmark error", error);
      toast.error("An error occurred");
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className={"flex gap-1 items-start"}>
          <span className={"flex-1"}>
            {paper.title}
          </span>

          <Button onClick={handleBookmark} variant="ghost" size="icon" className={"-mt-2"}>
            <Bookmark
                className={isBookmarked ? "fill-primary text-primary" : ""}
            />
          </Button>
        </CardTitle>

      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">
          {paper.authors.join(", ")}
        </p>
      </CardContent>
      <CardFooter>
      </CardFooter>
    </Card>
  );
}
