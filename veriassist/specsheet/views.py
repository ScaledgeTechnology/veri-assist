from django.shortcuts import render

# Create your views here.
def spec_index(request):
    return render(request, 'spec_index.html')