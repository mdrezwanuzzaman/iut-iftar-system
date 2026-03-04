async function login(){
    const student_id = document.getElementById("student_id").value;
    const password = document.getElementById("password").value;

    const res = await fetch("/login",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({student_id,password})
    });

    if(!res.ok){
        document.getElementById("error").innerText="Invalid Login";
        return;
    }

    window.location="/menu";
}

async function order(){
    const res = await fetch("/order",{method:"POST"});
    const data = await res.json();
    window.location="/track/"+data.order_id;
}

function track(orderId){
    setInterval(async ()=>{
        const res = await fetch("/status/"+orderId);
        const data = await res.json();

        document.getElementById("status").innerText=data.status;

        if(data.status==="Ready"){
            window.location="/ready/"+orderId;
        }
    },2000);
}
