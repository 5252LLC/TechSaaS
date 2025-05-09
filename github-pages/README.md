# TechSaaS.Tech Landing Page

This is the official landing page for [TechSaaS.Tech](https://techsaas.tech) hosted on GitHub Pages with custom domain and SSL.

## Features

- Modern, responsive design
- Dark mode by default
- SSL secured
- Custom domain integration
- Optimized for SEO

## Setting Up SSL for GitHub Pages with Custom Domain

To ensure your GitHub Pages site has SSL when using your custom domain TechSaaS.Tech:

1. In your GitHub repository settings, navigate to "Pages"
2. Under "Custom domain", enter `techsaas.tech`
3. Check "Enforce HTTPS" (GitHub will provision and manage SSL certificates automatically)
4. Ensure your DNS provider has the correct settings:
   - Type: A records
   - Host: @ (or leave blank)
   - Value: GitHub Pages IP addresses
     - 185.199.108.153
     - 185.199.109.153
     - 185.199.110.153
     - 185.199.111.153
   - TTL: 3600 (or default)

5. Add a CNAME record:
   - Type: CNAME
   - Host: www
   - Value: 5252LLC.github.io.
   - TTL: 3600 (or default)

## Updating the Landing Page

To update the landing page:

1. Make changes to the files in this directory
2. Commit and push to GitHub
3. GitHub Pages will automatically rebuild and deploy the site

```bash
git add .
git commit -m "Update landing page"
git push origin main
```

## Important URLs

- Live site: [https://techsaas.tech](https://techsaas.tech)
- GitHub repository: [https://github.com/5252LLC/TechSaaS](https://github.com/5252LLC/TechSaaS)
- Main application: [https://techsaas.tech/scraper](https://techsaas.tech/scraper)

## SSL Verification

The site uses GitHub Pages' built-in SSL capabilities, which are powered by Let's Encrypt. The certificates are automatically renewed by GitHub.
