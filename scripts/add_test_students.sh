#!/bin/bash
# Add test students to Supabase

cd /home/iot/attendance-system
export $(grep -v '^#' .env | xargs)

echo "Adding test students to Supabase..."

# Student 1: Juan Dela Cruz
curl -X POST "${SUPABASE_URL}/rest/v1/students" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_KEY}" \
  -H "Content-Type: application/json" \
  -H "Prefer: return=representation" \
  -d '{
    "student_number": "2021001",
    "first_name": "Juan",
    "last_name": "Dela Cruz",
    "grade_level": "11",
    "section": "STEM-A",
    "parent_guardian_contact": "+639480205567",
    "status": "active"
  }'

echo ""

# Student 2: Maria Santos
curl -X POST "${SUPABASE_URL}/rest/v1/students" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_KEY}" \
  -H "Content-Type: application/json" \
  -H "Prefer: return=representation" \
  -d '{
    "student_number": "2021002",
    "first_name": "Maria",
    "last_name": "Santos",
    "grade_level": "11",
    "section": "STEM-A",
    "parent_guardian_contact": "+639923783237",
    "status": "active"
  }'

echo ""

# Student 3: Pedro Reyes
curl -X POST "${SUPABASE_URL}/rest/v1/students" \
  -H "apikey: ${SUPABASE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_KEY}" \
  -H "Content-Type: application/json" \
  -H "Prefer: return=representation" \
  -d '{
    "student_number": "2021003",
    "first_name": "Pedro",
    "last_name": "Reyes",
    "grade_level": "12",
    "section": "ABM-B",
    "parent_guardian_contact": "+639480205567",
    "status": "active"
  }'

echo ""
echo "✅ Test students added to Supabase!"
