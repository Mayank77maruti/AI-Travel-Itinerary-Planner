from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Itinerary
from .serializers import ItinerarySerializer, ItineraryCreateSerializer
import os
import requests
import json
from rest_framework.decorators import api_view

def index(request):
    return render(request, 'index.html')

# Create your views here.

class ItineraryView(APIView):
    def post(self, request):
        serializer = ItineraryCreateSerializer(data=request.data)
        if serializer.is_valid():
            destination = serializer.validated_data['destination']
            days = serializer.validated_data['days']
            user_email = serializer.validated_data['user_email']
            
            # Call Groq API
            api_key = os.getenv('GROQ_API_KEY')
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            prompt = f"""Create a detailed {days}-day itinerary for {destination}. 
            Include:
            - Daily activities with timing
            - Restaurant recommendations for each meal
            - Transportation tips between locations
            - Estimated costs for major activities
            - Local customs and etiquette tips
            
            Format it as a clear day-by-day breakdown with sections for each day."""
            
            try:
                response = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers,
                    json={
                        "model": "meta-llama/llama-4-scout-17b-16e-instruct",
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": 0.7,
                        "max_tokens": 2000
                    }
                )
                
                if response.status_code != 200:
                    print(f"Error response: {response.text}")
                    return Response(
                        {'error': 'Failed to generate itinerary', 'details': response.text},
                        status=500
                    )
                
                result = response.json()['choices'][0]['message']['content']
                
                # Save to DB with user email
                itinerary = Itinerary.objects.create(
                    destination=destination,
                    days=days,
                    result=result,
                    user_email=user_email
                )
                return Response(ItinerarySerializer(itinerary).data, status=201)
                
            except Exception as e:
                print(f"Error calling Groq API: {str(e)}")  # For debugging
                if hasattr(e, 'response'):
                    print(f"Response status: {e.response.status_code}")
                    print(f"Response body: {e.response.text}")
                return Response(
                    {'error': 'Failed to generate itinerary', 'details': str(e)},
                    status=500
                )
        return Response(serializer.errors, status=400)

class HistoryView(APIView):
    def get(self, request):
        user_email = request.query_params.get('user_email')
        if not user_email:
            return Response({'error': 'user_email is required'}, status=400)
            
        itineraries = Itinerary.objects.filter(user_email=user_email).order_by('-created_at')
        data = [
            {
                'id': i.id,
                'destination': i.destination,
                'days': i.days,
                'result': i.result,
                'created_at': i.created_at,
                'user_email': i.user_email,
            } for i in itineraries
        ]
        return Response(data)
