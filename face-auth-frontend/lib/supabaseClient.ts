import { createClient, SupabaseClient } from '@supabase/supabase-js'

const url = process.env.NEXT_PUBLIC_SUPABASE_URL || ''
const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''

let client: SupabaseClient | null = null

export function getSupabaseClient(): SupabaseClient {
    // Defer creation to runtime (browser). Avoid creating on server where env may be unset.
    if (client) return client
    if (!url) {
        throw new Error('NEXT_PUBLIC_SUPABASE_URL is required to create Supabase client')
    }
    client = createClient(url, anonKey)
    return client
}

export default getSupabaseClient
