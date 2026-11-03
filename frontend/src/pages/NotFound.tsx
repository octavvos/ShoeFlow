import { Compass } from "lucide-react";
import { Link } from "react-router-dom";

import { Button, Card, EmptyState } from "@/components/ui";

export default function NotFoundPage() {
  return (
    <Card>
      <EmptyState
        icon={Compass}
        title="Sahifa topilmadi"
        text="Bu manzilda hech narsa yo'q yoki sizda ko'rish huquqi yo'q."
        action={
          <Link to="/">
            <Button>Bosh sahifaga</Button>
          </Link>
        }
      />
    </Card>
  );
}
