// Supabase Edge Function: Verify Signed Attendance URLs
// Deno Deploy runtime

import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

interface VerifyRequest {
  student_id: string
  expires: string
  sig: string
}

interface VerifyResponse {
  valid: boolean
  student_uuid?: string
  expires_at?: string
  error?: string
}

serve(async (req) => {
  // Handle CORS preflight
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    // Parse query parameters
    const url = new URL(req.url)
    const student_id = url.searchParams.get('student_id')
    const expires = url.searchParams.get('expires')
    const sig = url.searchParams.get('sig')

    // Validate required parameters
    if (!student_id || !expires || !sig) {
      return new Response(
        JSON.stringify({
          valid: false,
          error: 'Missing required parameters: student_id, expires, sig'
        } as VerifyResponse),
        {
          status: 400,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        }
      )
    }

    // Check expiration (before expensive signature verification)
    const expiresTimestamp = parseInt(expires)
    const now = Math.floor(Date.now() / 1000)
    
    if (isNaN(expiresTimestamp)) {
      return new Response(
        JSON.stringify({
          valid: false,
          error: 'Invalid expiration timestamp'
        } as VerifyResponse),
        {
          status: 400,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        }
      )
    }

    if (now > expiresTimestamp) {
      return new Response(
        JSON.stringify({
          valid: false,
          error: 'Link has expired'
        } as VerifyResponse),
        {
          status: 403,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        }
      )
    }

    // Get signing secret from environment
    const signingSecret = Deno.env.get('SIGNING_SECRET')
    if (!signingSecret) {
      console.error('SIGNING_SECRET not configured')
      return new Response(
        JSON.stringify({
          valid: false,
          error: 'Server configuration error'
        } as VerifyResponse),
        {
          status: 500,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        }
      )
    }

    // Verify HMAC signature
    const message = `${student_id}:${expires}`
    const encoder = new TextEncoder()
    const key = await crypto.subtle.importKey(
      'raw',
      encoder.encode(signingSecret),
      { name: 'HMAC', hash: 'SHA-256' },
      false,
      ['sign']
    )
    
    const signature = await crypto.subtle.sign(
      'HMAC',
      key,
      encoder.encode(message)
    )
    
    const expectedSig = Array.from(new Uint8Array(signature))
      .map(b => b.toString(16).padStart(2, '0'))
      .join('')

    if (sig !== expectedSig) {
      console.warn(`Invalid signature for student ${student_id}`)
      return new Response(
        JSON.stringify({
          valid: false,
          error: 'Invalid signature - link may have been tampered with'
        } as VerifyResponse),
        {
          status: 403,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' }
        }
      )
    }

    // Signature is valid! Return success
    const expiresAt = new Date(expiresTimestamp * 1000).toISOString()
    
    console.log(`✅ Valid signed URL: student=${student_id}, expires=${expiresAt}`)
    
    return new Response(
      JSON.stringify({
        valid: true,
        student_uuid: student_id,
        expires_at: expiresAt
      } as VerifyResponse),
      {
        status: 200,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    )

  } catch (error) {
    console.error('Error verifying URL:', error)
    return new Response(
      JSON.stringify({
        valid: false,
        error: 'Verification failed'
      } as VerifyResponse),
      {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    )
  }
})
