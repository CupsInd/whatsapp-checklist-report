let users = [
    {
        id: 1,
        name: "Andi",
        profile: { age: 25, city: "Surabaya" },
        status: "active"
    },
    {
        id: 2,
        name: "Budi",
        profile: { age: 17, city: "Malang" },
        status: "inactive"
    }
];

let adult = users.filter(u => u.profile.age >= 18);
let isAdult = users.map(u => ({
    ...u,
    isAdult: u.profile.age >= 18,
}));
let statusData = {
    active: "Aktif",
    inactive: "Tidak Aktif"
}; 
console.log(adult);
console.log(isAdult);
console.log(statusData);
