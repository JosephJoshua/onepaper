import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export default function PaperCardSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-5 w-4/5" />
        <Skeleton className="h-5 w-2/5" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-4 w-full mb-2" />
        <Skeleton className="h-4 w-1/3" />
      </CardContent>
    </Card>
  );
}
