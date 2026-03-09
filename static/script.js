<script>

function addToCart(productId){

fetch("/add_to_cart", {

method:"POST",

headers:{
"Content-Type":"application/json"
},

body: JSON.stringify({
product_id: productId
})

})

.then(response => response.json())

.then(data => {

document.getElementById("cart-count").innerText = data.cart_count;

})

}

</script>