let orders = [
    { id: 1, user: "Andi", category: "Elektronik", total: 1500000, status: "paid" },
    { id: 2, user: "Budi", category: "Fashion", total: 500000, status: "paid" },
    { id: 3, user: "Citra", category: "Elektronik", total: 2000000, status: "unpaid" },
    { id: 4, user: "Dina", category: "Elektronik", total: 1000000, status: "paid" },
    { id: 5, user: "Eka", category: "Fashion", total: 750000, status: "paid" },
];

//Function 
function salesAnalytics(orders) {
//Total revenue (paid only)
let totalRevenue = orders.reduce((r, o) => {
    if (o.status === "paid") {
        return r + o.total;
    } return r;
}, 0);
//TOtal revenue by category
let revenueByCategory = orders.reduce((r, o) => {
    if (o.status === "paid") {
        r[o.category] = (r[o.category] || 0) + o.total;
    } return r;
}, {});
//user spending summary
let spendingByUser = orders.reduce((r, o) => {
    if (o.status === "paid") {
        r[o.user] = (r[o.user] || 0) + o.total;
    } return r;
}, {});
//highest value order
let highestOrderValue = orders.reduce((max, o) => {
    if ((o.status === "paid") && (o.total > max)) {
        return o.total;
    } return max;
    }, 0);
let highestOrder = orders.find(o => o.total === highestOrderValue);
//business helath check
///cek unpaid order
let hasUnpaid = orders.some(o => o.status === "unpaid");
///all order >0
let allValid = orders.every(o => o.total > 0);
return {
    totalRevenue,
    revenueByCategory,
    spendingByUser,
    highestOrder,
    hasUnpaid,
    allValid
}
}
let hasil = salesAnalytics(orders);
console.log("--- REKAP PENJUALAN ---");
console.log("Total penjualan =Rp. " + hasil.totalRevenue);
console.log("Total penjualan tiap Category =Rp. " + hasil.revenueByCategory);
console.log("Spending setiap user =")
console.log(hasil.spendingByUser);
console.log("Spending/Pembelian terbesar =");
console.log(hasil.highestOrder);
console.log("cek pembayaran = " + (hasil.hasUnpaid ? "ada yang belum terbayar" : "semua terbayar"));
console.log("cek total item terjual = " + (hasil.allValid ? "data terjual aman" : "data terjual ada yang 0 (nol)"));