import { useEffect, useState } from "react";
import axios from "axios";
import "./PurchasesPage.css";

function PurchasesPage() {
  const [purchases, setPurchases] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchPurchases = async () => {
      try {
        const token = localStorage.getItem("token");
        const response = await axios.get("http://localhost:5000/my-purchases", {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        setPurchases(response.data);
      } catch (err) {
        console.error("Failed to fetch purchases:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchPurchases();
  }, []);

  if (loading) {
    return <div className="purchases-container">Loading purchases...</div>;
  }

  return (
    <div className="purchases-container">
      <h2>Your Purchases</h2>
      {purchases.length === 0 ? (
        <p>You haven't purchased anything yet.</p>
      ) : (
        <div className="purchases-list">
          {purchases.map((purchase) => (
            <div key={purchase.purchase_id} className="purchase-card">
              {purchase.image_url && (
                <img src={purchase.image_url} alt={purchase.title} />
              )}
              <div className="purchase-info">
                <h3>{purchase.title}</h3>
                <p>Price: ${purchase.price.toFixed(2)}</p>
                <p>
                  Seller: {purchase.seller.first_name}{" "}
                  {purchase.seller.last_name} (@{purchase.seller.handle})
                </p>
                <p className="date">
                  Purchased on {new Date(purchase.purchased_at).toLocaleDateString()}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default PurchasesPage;
