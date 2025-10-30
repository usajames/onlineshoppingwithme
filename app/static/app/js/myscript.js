$('#slider1, #slider2, #slider3, #slider4, #slider5').owlCarousel({
    loop: true,
    margin: 20,
    responsiveClass: true,
    responsive: {
        0: { items: 1, nav:
             false, autoplay:
              true },
        600: { items: 3, nav:
             true, autoplay:
              true },
        1000: { items: 5, nav:
             true, loop:
             
             true, autoplay: 
             true }
    }
});

// CSRF helper and cart AJAX updates
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

document.addEventListener('DOMContentLoaded', function () {
    const csrftoken = getCookie('csrftoken');

    function postCartUpdate(cartId, action) {
        const formData = new FormData();
        formData.append('cart_id', cartId);
        formData.append('action', action);

        return fetch('/api/cart/update/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrftoken
            },
            body: formData,
            credentials: 'same-origin'
        }).then(r => r.json());
    }

    document.querySelectorAll('.cart-update').forEach(function (el) {
        el.addEventListener('click', function (ev) {
            ev.preventDefault();
            const cartId = this.getAttribute('data-cart-id');
            const action = this.getAttribute('data-action');

            postCartUpdate(cartId, action).then(function (data) {
                if (data && data.success) {
                    // update item quantity and line total
                    const qSpan = document.getElementById('quantity-' + data.cart_id);
                    const ltSpan = document.getElementById('line-total-' + data.cart_id);
                    if (qSpan) qSpan.textContent = data.quantity;
                    if (ltSpan) ltSpan.textContent = parseFloat(data.line_total).toFixed(2);

                    // update totals
                    const amountEl = document.getElementById('cart-amount');
                    const shippingEl = document.getElementById('cart-shipping');
                    const totalEl = document.getElementById('cart-total');
                    if (amountEl) amountEl.textContent = parseFloat(data.amount).toFixed(2);
                    if (shippingEl) shippingEl.textContent = parseFloat(data.shipping).toFixed(2);
                    if (totalEl) totalEl.textContent = parseFloat(data.total).toFixed(2);

                    // if item removed (quantity 0) hide the item row
                    if (data.quantity === 0) {
                        const row = document.getElementById('cart-row-' + data.cart_id);
                        if (row) row.remove();
                    }
                }
            }).catch(function (err) {
                console.error('Cart update failed', err);
            });
        });
    });
});
