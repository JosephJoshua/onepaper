"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { toast } from "sonner";
import api from "@/lib/api";
import { useAuth } from "@/context/auth-context";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

// Regex for common arXiv ID formats (e.g., 2310.06825, cs/0703150)
const arxivIdRegex = /^(\d{4}\.\d{4,5}|[a-z\-]+\/\d{7})(v\d+)?$/;

const formSchema = z.object({
  arxivId: z
    .string()
    .regex(
      arxivIdRegex,
      "Please enter a valid arXiv ID (e.g., 2310.06825 or cs/0703150).",
    ),
});

export default function SubmitPage() {
  const { isAuthenticated } = useAuth();
  const router = useRouter();

  useEffect(() => {
    // Redirect to login if not authenticated
    if (!localStorage.getItem("token")) {
      router.push("/login");
    }
  }, [router]);

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: { arxivId: "" },
  });

  async function onSubmit(values: z.infer<typeof formSchema>) {
    toast.info("Submitting paper for processing...");
    try {
      await api.post("/papers/submit", {
        arxiv_id: values.arxivId,
      });

      router.push(`/submit/status?arxivId=${values.arxivId}`);
      form.reset(); // Clear the form on success
    } catch (error: unknown) {
      const detail =
          // @ts-expect-error doesn't matter
          error.response?.data?.detail || "An unknown error occurred.";

      toast.error("Submission Failed", {
        description: detail,
      });

      console.error(error);
    }
  }

  if (!isAuthenticated) {
    return <div>Loading...</div>; // Or a loading spinner
  }

  return (
    <div className="flex justify-center items-center mt-10">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <CardTitle>Submit a New Paper</CardTitle>
          <CardDescription>
            Enter an arXiv ID to fetch, analyze, and add a paper to the
            platform.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
              <FormField
                control={form.control}
                name="arxivId"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>arXiv ID</FormLabel>
                    <FormControl>
                      <Input placeholder="e.g., 2310.06825" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <Button
                type="submit"
                className="w-full"
                disabled={form.formState.isSubmitting}
              >
                {form.formState.isSubmitting
                  ? "Submitting..."
                  : "Submit for Processing"}
              </Button>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  );
}
