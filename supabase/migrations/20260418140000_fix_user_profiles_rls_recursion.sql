-- Policies that do EXISTS (SELECT ... FROM user_profiles ...) while evaluating
-- RLS on user_profiles cause PostgreSQL "infinite recursion detected in policy
-- for relation user_profiles" → PostgREST 500. Use a SECURITY DEFINER helper
-- that reads the row without tripping nested RLS checks.

CREATE OR REPLACE FUNCTION public.auth_is_super_admin()
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
STABLE
AS $$
DECLARE
  flag boolean;
BEGIN
  PERFORM set_config('row_security', 'off', true);
  SELECT is_super_admin INTO flag
  FROM public.user_profiles
  WHERE id = auth.uid();
  RETURN COALESCE(flag, false);
END;
$$;

COMMENT ON FUNCTION public.auth_is_super_admin() IS
  'True when auth.uid() is a platform super admin. SECURITY DEFINER + row_security=off avoids RLS self-recursion.';

REVOKE ALL ON FUNCTION public.auth_is_super_admin() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.auth_is_super_admin() TO authenticated;
GRANT EXECUTE ON FUNCTION public.auth_is_super_admin() TO service_role;

DROP POLICY IF EXISTS "Super admins can manage all businesses" ON public.businesses;
CREATE POLICY "Super admins can manage all businesses"
    ON public.businesses FOR ALL
    USING (public.auth_is_super_admin());

DROP POLICY IF EXISTS "Super admins can view all profiles" ON public.user_profiles;
CREATE POLICY "Super admins can view all profiles"
    ON public.user_profiles FOR SELECT
    USING (public.auth_is_super_admin());

DROP POLICY IF EXISTS "Super admins manage members" ON public.business_members;
CREATE POLICY "Super admins manage members"
    ON public.business_members FOR ALL
    USING (public.auth_is_super_admin());
