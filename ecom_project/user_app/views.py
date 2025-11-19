from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from .models import *
from .forms import *

def session_register(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        password2 = request.POST.get("password2")
        if password != password2:
            messages.error(request, "Passwords do not match")
        elif User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
        else:
            user = User.objects.create_user(username=username, email=email, password=password)
            Profile.objects.create(user=user)
            messages.success(request, "Registration successful! Login now.")
            return redirect("session_login")
    return render(request, "register.html")

def session_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect("session_dashboard")
        else:
            messages.error(request, "Invalid credentials")
    return render(request, "login.html")

@login_required
def session_dashboard(request):
    return render(request, "dashboard.html")

@login_required
def session_logout(request):
    request.session.flush()
    logout(request)
    return redirect("session_login")


@login_required
def profile_view(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    is_empty = not profile.full_name and not profile.phone and not profile.address
    return render(request, "profile_view.html", {"profile": profile, "is_empty": is_empty})

@login_required
def profile_edit(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    form = ProfileForm(request.POST or None, instance=profile)
    if form.is_valid():
        form.save()
        return redirect("profile_view")
    return render(request, "profile_edit.html", {"form": form})


def is_admin(user):
    return user.is_superuser


@user_passes_test(is_admin)
def product_create(request):
    form = ProductForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        form.save()
        return redirect("product_list")
    return render(request, "product_create.html", {"form": form})

def product_list(request):
    products = Product.objects.all()
    recently_viewed = request.session.get("recently_viewed", [])

    recent_products = Product.objects.filter(id__in=recently_viewed)
    recent_products = sorted(recent_products, key=lambda p: recently_viewed.index(p.id))

    return render(request, "product_list.html", {
        "products": products,
        "recent_products": recent_products
    })

def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    recently_viewed = request.session.get("recently_viewed", [])
    if pk in recently_viewed:
        recently_viewed.remove(pk)
    recently_viewed.insert(0, pk)  
    request.session["recently_viewed"] = recently_viewed[:5]  
    print("Recently viewed:", request.session.get("recently_viewed"))

    return render(request, "product_detail.html", {"product": product})


@user_passes_test(is_admin)
def product_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ProductForm(request.POST or None, request.FILES or None, instance=product)
    if form.is_valid():
        form.save()
        return redirect("product_list")
    return render(request, "product_update.html", {"form": form})

@user_passes_test(is_admin)
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.delete()
    return redirect("product_list")


@login_required
def add_to_cart(request, product_id):
    cart = request.session.get("cart", {})
    cart[str(product_id)] = cart.get(str(product_id), 0) + 1
    request.session["cart"] = cart

    print("Session cart:", request.session["cart"])
    return redirect("view_cart")

@login_required
def update_cart(request, product_id):
    if request.method == "POST":
        cart = request.session.get("cart", {})
        qty = int(request.POST.get("quantity", 1))
        if qty > 0:
            cart[str(product_id)] = qty
        else:
            cart.pop(str(product_id), None)
        request.session["cart"] = cart
    print("Session cart:", request.session.get("cart"))
    return redirect("view_cart")

@login_required
def view_cart(request):
    cart = request.session.get("cart", {})
    items = []
    total = 0
    for pid, qty in cart.items():
        p = Product.objects.get(id=pid)
        items.append({"product": p, "qty": qty, "subtotal": p.price * qty})
        total += p.price * qty
    print("Cart total:", total)
    return render(request, "cart.html", {"items": items, "total": total})

@login_required
def remove_from_cart(request, product_id):
    cart = request.session.get("cart", {})
    if str(product_id) in cart:
        del cart[str(product_id)]
    request.session["cart"] = cart
    return redirect("view_cart")

@login_required
def checkout(request):
    cart = request.session.get("cart", {})
    if not cart:
        return redirect("view_cart")
    total = 0
    order = Order.objects.create(user=request.user, total=0)
    for pid, qty in cart.items():
        p = Product.objects.get(id=pid)
        total += p.price * qty
        OrderItem.objects.create(order=order, product=p, quantity=qty, price=p.price)
    order.total = total
    order.save()
    del request.session["cart"]
    return redirect("order_list")


@login_required
def order_list(request):
    if request.user.is_superuser:
        orders = Order.objects.all()
    else:
        orders = Order.objects.filter(user=request.user)
    return render(request, "order_list.html", {"orders": orders})

@user_passes_test(is_admin)
def order_update(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == "POST":
        order.status = request.POST.get("status")
        order.save()
        return redirect("order_list")
    return render(request, "order_update.html", {"order": order})

@user_passes_test(is_admin)
def order_delete(request, pk):
    Order.objects.get(pk=pk).delete()
    return redirect("order_list")
